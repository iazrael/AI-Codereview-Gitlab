import os
import markdown
from datetime import datetime
from biz.utils.log import logger


class HTMLReporter:
    def __init__(self, reports_dir="/app/data/reports"):
        """
        初始化HTML报告生成器
        :param reports_dir: 报告存储目录
        """
        self.reports_dir = reports_dir
        # 确保报告目录存在
        os.makedirs(self.reports_dir, exist_ok=True)
    
    def generate_html_report(self, markdown_content: str, date_str: str = None) -> str:
        """
        将Markdown内容转换为HTML报告
        :param markdown_content: Markdown格式的报告内容
        :param date_str: 报告日期(YYYY-MM-DD格式)，如果未提供则使用当前日期
        :return: HTML格式的报告内容
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        # 转换Markdown为HTML
        html_content = markdown.markdown(markdown_content, extensions=['extra', 'codehilite'])
        
        # 应用模板
        html_report = self._apply_template(html_content, date_str)
        
        return html_report
    
    def _apply_template(self, content: str, date_str: str) -> str:
        """
        应用HTML模板
        :param content: 报告内容
        :param date_str: 报告日期
        :return: 带模板的完整HTML
        """
        template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>代码审查日报 - {date_str}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            padding: 20px;
            background-color: #f8f9fa;
        }}
        .header {{
            background-color: #fff;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,.1);
        }}
        .content {{
            background-color: #fff;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,.1);
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #6c757d;
            font-size: 0.9em;
        }}
        h1, h2, h3 {{
            color: #2c3e50;
        }}
        .author-section {{
            border-left: 4px solid #007bff;
            padding-left: 15px;
            margin-bottom: 25px;
        }}
        code {{
            background-color: #f1f1f1;
            padding: 2px 4px;
            border-radius: 4px;
        }}
        pre {{
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 12px;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="display-4">代码审查日报</h1>
            <p class="lead">生成时间: {date_str}</p>
        </div>
        
        <div class="content">
            {content}
        </div>
        
        <div class="footer">
            <p>AI代码审查系统 &copy; {datetime.now().year}</p>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""
        return template
    
    def save_report(self, html_content: str, date_str: str = None, filename: str = None) -> str:
        """
        保存HTML报告到文件
        :param html_content: HTML格式的报告内容
        :param date_str: 报告日期(YYYYMMDD格式)，如果未提供则使用当前日期
        :return: 保存的文件路径
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")
        
        filename = f"{filename}.html"
        filepath = os.path.join(self.reports_dir, date_str, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"{date_str} HTML报告已保存到: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"{date_str} 保存HTML报告失败: {e}")
            raise
    
    def get_report_list(self) -> list:
        """
        获取报告列表
        :return: 报告文件列表
        """
        try:
            reports = []
            for file in os.listdir(self.reports_dir):
                if file.startswith("report_") and file.endswith(".html"):
                    reports.append(file)
            # 按日期倒序排列
            reports.sort(reverse=True)
            return reports
        except Exception as e:
            logger.error(f"获取报告列表失败: {e}")
            return []