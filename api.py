from dotenv import load_dotenv

load_dotenv("conf/.env")

import atexit
import json
import os
import traceback
from datetime import datetime
from urllib.parse import urlparse
import sys
# 把当前目录加到path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask, request, jsonify

from biz.queue.worker import handle_merge_request_event, handle_push_event, handle_github_pull_request_event, \
    handle_github_push_event, handle_gitea_pull_request_event, handle_gitea_push_event
from biz.coding.webhook_handler import handle_coding_pull_request_event, handle_coding_push_event
from biz.git_provider.manager import GitProviderManager
from biz.git_provider.parsers import gitlab_parser, github_parser, gitea_parser, coding_parser
import importlib
from biz.service.review_service import ReviewService
from biz.utils.im import notifier
from biz.utils.log import logger
from biz.utils.queue import handle_queue
from biz.utils.reporter import Reporter
from biz.utils.html_reporter import HTMLReporter

from biz.utils.config_checker import check_config

api_app = Flask(__name__)

# 初始化GitProviderManager
git_provider_manager = GitProviderManager()

push_review_enabled = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'


@api_app.route('/')
def home():
    return """<h2>The code review api server is running.</h2>
              <p>GitHub project address: <a href="https://github.com/sunmh207/AI-Codereview-Gitlab" target="_blank">
              https://github.com/sunmh207/AI-Codereview-Gitlab</a></p>
              <p>Gitee project address: <a href="https://gitee.com/sunminghui/ai-codereview-gitlab" target="_blank">https://gitee.com/sunminghui/ai-codereview-gitlab</a></p>
              """


@api_app.route('/review/daily_report', methods=['GET'])
def daily_report():
    # 获取当前日期0点和23点59分59秒的时间戳
    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end_time = datetime.now().replace(hour=23, minute=59, second=59, microsecond=0).timestamp()

    try:
        if push_review_enabled:
            df = ReviewService().get_push_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)
        else:
            df = ReviewService().get_mr_review_logs(updated_at_gte=start_time, updated_at_lte=end_time)

        if df.empty:
            logger.info("No data to process.")
            return jsonify({'message': 'No data to process.'}), 200
        # 去重：基于 (author, message) 组合
        df_unique = df.drop_duplicates(subset=["author", "commit_messages"])
        # 按照 author 排序
        df_sorted = df_unique.sort_values(by="author")
        # 转换为适合生成日报的格式
        commits = df_sorted.to_dict(orient="records")
        # 生成日报内容
        report_txt = Reporter().generate_report(json.dumps(commits))
        # 生成HTML报告并保存
        html_reporter = HTMLReporter()
        html_content = html_reporter.generate_html_report(report_txt)
        today_str = datetime.now().strftime("%Y%m%d")
        html_reporter.save_report(html_content, today_str, 'daily_report')
        
        # 获取域名用于报告链接
        domain = os.environ.get('SERVER_DOMAIN', f'http://localhost:{os.environ.get("SERVER_PORT", 5001)}')
        report_url = f"{domain}/reports/{today_str}/daily_report.html"
        
        # 在通知中添加报告链接
        report_link = f"\n\n[查看详细报告]({report_url})"
        report_txt_with_link = report_txt + report_link
        
        # 发送钉钉通知
        notifier.send_notification(content=report_txt_with_link, msg_type="markdown", title="代码提交日报")

        # 返回生成的日报内容
        return json.dumps(report_txt, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        return jsonify({'message': f"Failed to generate daily report: {e}"}), 500


def setup_scheduler():
    """
    配置并启动定时任务调度器
    """
    try:
        scheduler = BackgroundScheduler()
        crontab_expression = os.getenv('REPORT_CRONTAB_EXPRESSION', '0 18 * * 1-5')
        cron_parts = crontab_expression.split()
        cron_minute, cron_hour, cron_day, cron_month, cron_day_of_week = cron_parts

        # Schedule the task based on the crontab expression
        scheduler.add_job(
            daily_report,
            trigger=CronTrigger(
                minute=cron_minute,
                hour=cron_hour,
                day=cron_day,
                month=cron_month,
                day_of_week=cron_day_of_week
            )
        )

        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started successfully.")

        # Shut down the scheduler when exiting the app
        atexit.register(lambda: scheduler.shutdown())
    except Exception as e:
        logger.error(f"Error setting up scheduler: {e}")
        logger.error(traceback.format_exc())


# 处理 GitLab Merge Request Webhook
@api_app.route('/review/webhook', methods=['POST'])
def handle_webhook():
    # 获取请求的JSON数据
    if not request.is_json:
        return jsonify({'message': 'Invalid data format'}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    # logger.info(f"Received webhook headers: {request.headers}")
    logger.info(f"Received webhook data: {data}")
    # 识别Git提供方
    provider_config = git_provider_manager.identify_provider(request.headers)

    if not provider_config:
        logger.error(f"Unknown Git provider or unsupported webhook event")
        return jsonify({"error": "Unknown Git provider or unsupported webhook event"}), 400

    provider_name = provider_config["name"]
    # 获取访问令牌
    access_token = git_provider_manager.get_access_token(provider_config, request.headers)
    if not access_token:
        logger.error(f"Missing {provider_name} access token")
        return jsonify({'message': f'Missing {provider_name} access token'}), 400

    # 获取原始事件类型
    original_event_type = None
    for header_name, expected_values in provider_config["identification"]["headers"].items():
        original_event_type = request.headers.get(header_name)
        if original_event_type:
            break

    if not original_event_type:
        logger.error(f"Could not determine original event type from headers")
        return jsonify({"error": "Could not determine original event type"}), 400

    # 映射到内部事件类型
    event_type = git_provider_manager.get_event_mapping(provider_config, original_event_type)
    if not event_type:
        logger.error(f"Unsupported event type: {original_event_type} for {provider_name}")
        return jsonify({"error": f"Unsupported event type: {original_event_type} for {provider_name}"}), 400

    # 动态加载并调用payload解析器
    parser_path = git_provider_manager.get_payload_parser_path(provider_config)
    if not parser_path:
        logger.error(f"No payload parser defined for {provider_name}")
        return jsonify({"error": f"No payload parser defined for {provider_name}"}), 400

    try:
        module_name, func_name = parser_path.rsplit('.', 1)
        parser_module = importlib.import_module(module_name)
        parser_func = getattr(parser_module, func_name)
    except (ImportError, AttributeError) as e:
        logger.error(f"Failed to load parser for {provider_name}: {e}")
        return jsonify({"error": f"Failed to load parser for {provider_name}: {e}"}), 500

    try:
        # 根据不同的解析器函数签名传递参数
        if provider_name == "github":
            webhook_event = parser_func(data, access_token, os.getenv('GITHUB_URL'), event_type)
        elif provider_name == "gitea":
            webhook_event = parser_func(data, access_token, os.getenv('GITEA_URL'), event_type)
        elif provider_name == "gitlab":
            webhook_event = parser_func(data, access_token, os.getenv('GITLAB_URL'))
        elif provider_name == "coding":
            webhook_event = parser_func(data, access_token, os.getenv('CODING_URL'), event_type)
        else:
            # 对于自定义提供方，可能需要更通用的解析器，或者在配置中指定所有必要参数
            webhook_event = parser_func(data, access_token, os.getenv(f'{provider_name.upper()}_URL'), event_type)

    except ValueError as e:
        logger.error(f"Error parsing payload for {provider_name}: {e}")
        return jsonify({"error": str(e)}), 400

    logger.info(f'Received {provider_name} event: {webhook_event.event_type}')
    logger.info(f'Payload: {json.dumps(data)}')

    # 根据事件类型调用相应的处理函数
    if webhook_event.event_type == "pull_request":
        if provider_name == "github":
            handle_queue(handle_github_pull_request_event, webhook_event.payload, webhook_event.token, webhook_event.url, webhook_event.url_slug)
        elif provider_name == "gitea":
            handle_queue(handle_gitea_pull_request_event, webhook_event.payload, webhook_event.token, webhook_event.url, webhook_event.url_slug)
        elif provider_name == "gitlab":
            handle_queue(handle_merge_request_event, webhook_event.payload, webhook_event.token, webhook_event.url, webhook_event.url_slug)
        elif provider_name == "coding":
            # 假设 Coding 的 pull request 事件由 handle_coding_pull_request_event 处理
            # 你需要创建 handle_coding_pull_request_event 函数
            handle_queue(handle_coding_pull_request_event, webhook_event.payload, webhook_event.token, webhook_event.url, webhook_event.url_slug)
        else:
            logger.error(f"Unsupported pull_request event for {provider_name}")
            # 对于自定义提供方，需要一个通用的pull request处理函数
            return jsonify({"error": f"Unsupported pull_request event for {provider_name}"}), 400
    elif webhook_event.event_type == "push":
        if provider_name == "github":
            handle_queue(handle_github_push_event, webhook_event.payload, webhook_event.token, webhook_event.url, webhook_event.url_slug)
        elif provider_name == "gitea":
            handle_queue(handle_gitea_push_event, webhook_event.payload, webhook_event.token, webhook_event.url, webhook_event.url_slug)
        elif provider_name == "gitlab":
            handle_queue(handle_push_event, webhook_event.payload, webhook_event.token, webhook_event.url, webhook_event.url_slug)
        elif provider_name == "coding":
            # 假设 Coding 的 push 事件由 handle_coding_push_event 处理
            # 你需要创建 handle_coding_push_event 函数
            handle_queue(handle_coding_push_event, webhook_event.payload, webhook_event.token, webhook_event.url, webhook_event.url_slug)
        else:
            # 对于自定义提供方，需要一个通用的push处理函数
            logger.error(f"Unsupported push event for {provider_name}")
            return jsonify({"error": f"Unsupported push event for {provider_name}"}), 400
    else:
        error_message = f'Unsupported event type: {webhook_event.event_type} for {provider_name}.'
        logger.error(error_message)
        return jsonify(error_message), 400

    return jsonify({'message': f'{provider_name} request received(event_type={webhook_event.event_type}), will process asynchronously.'}), 200


# 添加报告访问路由
@api_app.route('/reports/')
def list_reports():
    """获取报告列表"""
    try:
        html_reporter = HTMLReporter()
        reports = html_reporter.get_report_list()
        return jsonify(reports)
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        return jsonify({'message': f"Failed to list reports: {e}"}), 500


@api_app.route('/reports/<date>/<filename>.html')
def get_report(date, filename):
    """获取指定日期的报告"""
    try:
        
        # 构造文件路径
        reports_dir = "/app/data/reports"
        filepath = os.path.join(reports_dir, f"{date}/{filename}.html")
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            return jsonify({'message': 'Report not found'}), 404
            
        # 返回HTML文件内容
        return open(filepath, 'r', encoding='utf-8').read(), 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        logger.error(f"Failed to get report: {e}")
        return jsonify({'message': f"Failed to get report: {e}"}), 500


if __name__ == '__main__':
    check_config()
    # 启动定时任务调度器
    setup_scheduler()

    # 启动Flask API服务
    port = int(os.environ.get('SERVER_PORT', 5001))
    api_app.run(host='0.0.0.0', port=port)