import os
from datetime import datetime
from blinker import Signal

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.service.review_service import ReviewService
from biz.utils.im import notifier
from biz.utils.html_reporter import HTMLReporter

# 定义全局事件管理器（事件信号）
event_manager = {
    "merge_request_reviewed": Signal(),
    "push_reviewed": Signal(),
}


# 定义事件处理函数
def on_merge_request_reviewed(mr_review_entity: MergeRequestReviewEntity):
    # 发送IM消息通知
    # 格式化updated_at时间为 yyyy-MM-dd HH:mm:ss，时区用 env配置的 TZ
    tz_env = os.environ.get('TZ', 'UTC')
    try:
        # 假设 updated_at 是整数 Unix 时间戳，尝试解析
        updated_at_dt = datetime.fromtimestamp(mr_review_entity.updated_at)
        # 格式化为 yyyy-MM-dd HH:mm:ss
        formatted_updated_at = updated_at_dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError):
        # 如果解析失败，使用原始值
        formatted_updated_at = mr_review_entity.updated_at

    im_msg = f"""
### 🔀 {mr_review_entity.project_name}: Merge Request

#### 合并请求信息:
- **提交者:** <at id='{mr_review_entity.author}'></at>

- **源分支**: {mr_review_entity.source_branch}
- **目标分支**: {mr_review_entity.target_branch}
- **更新时间**: {formatted_updated_at}
- **提交信息:** {mr_review_entity.commit_messages}

- [查看合并详情]({mr_review_entity.url})

- **AI Review 结果:** 

{mr_review_entity.review_result}
    """
    
    # 生成静态HTML报告
    html_reporter = HTMLReporter()
        # 生成HTML报告
    html_content = html_reporter.generate_html_report(im_msg)
    # 使用日期和last_commit_id作为文件名
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{date_str}_{mr_review_entity.last_commit_id}"
    html_reporter.save_report(html_content, filename)
    
    # 获取域名用于报告链接
    domain = os.environ.get('SERVER_DOMAIN', f'http://localhost:{os.environ.get("SERVER_PORT", 5001)}')
    report_url = f"{domain}/reports/{filename}.html"
    
    # 在通知中添加报告链接
    report_link = f"\n\n[查看详细报告]({report_url})"
    im_msg += report_link
    
    notifier.send_notification(content=im_msg, msg_type='markdown', title='Merge Request Review',
                               project_name=mr_review_entity.project_name, url_slug=mr_review_entity.url_slug,
                               webhook_data=mr_review_entity.webhook_data)

    # 记录到数据库
    ReviewService().insert_mr_review_log(mr_review_entity)


def on_push_reviewed(entity: PushReviewEntity):
    # 发送IM消息通知
    im_msg = f"### 🚀 {entity.project_name}: Push\n\n"
    im_msg += "#### 提交记录:\n"

    tz_env = os.environ.get('TZ', 'UTC')
    for commit in entity.commits:
        message = commit.get('message', '').strip()
        author = commit.get('author', 'Unknown Author')
        timestamp = commit.get('timestamp', '')
        url = commit.get('url', '#')
        
        # 格式化 timestamp
        try:
            # 假设 timestamp 是整数 Unix 时间戳，尝试解析
            timestamp_dt = datetime.fromtimestamp(timestamp)
            # 格式化为 yyyy-MM-dd HH:mm:ss
            formatted_timestamp = timestamp_dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            # 如果解析失败，尝试作为字符串解析
            try:
                timestamp_dt = datetime.fromisoformat(timestamp)
                formatted_timestamp = timestamp_dt.strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, TypeError):
                # 如果还是失败，使用原始值
                formatted_timestamp = timestamp
        
        im_msg += (
            f"- **提交信息**: {message}\n"
            f"- **提交者**: {author}\n"
            f"- **时间**: {formatted_timestamp} ({tz_env})\n"
            f"- [查看提交详情]({url})\n\n"
        )

    if entity.review_result:
        im_msg += f"#### AI Review 结果: \n {entity.review_result}\n\n"
        
    # 生成静态HTML报告
    html_reporter = HTMLReporter()
    # 使用日期和第一个commit的ID作为文件名（如果没有commit ID，则使用随机字符串）
    date_str = datetime.now().strftime("%Y%m%d")
    first_commit_id = entity.commits[0]['id'][:8] if entity.commits and 'id' in entity.commits[0] else 'unknown'
    filename = f"{date_str}_{first_commit_id}"
    html_reporter.save_report(html_reporter.generate_html_report(im_msg), filename)
    
    # 获取域名用于报告链接
    domain = os.environ.get('SERVER_DOMAIN', f'http://localhost:{os.environ.get("SERVER_PORT", 5001)}')
    report_url = f"{domain}/reports/{filename}.html"
    
    # 在通知中添加报告链接
    report_link = f"\n\n[查看详细报告]({report_url})"
    im_msg += report_link
    
    notifier.send_notification(content=im_msg, msg_type='markdown',title=f"{entity.project_name} Push Event",
                               project_name=entity.project_name, url_slug=entity.url_slug,
                               webhook_data=entity.webhook_data)

    # 记录到数据库
    ReviewService().insert_push_review_log(entity)


# 连接事件处理函数到事件信号
event_manager["merge_request_reviewed"].connect(on_merge_request_reviewed)
event_manager["push_reviewed"].connect(on_push_reviewed)
