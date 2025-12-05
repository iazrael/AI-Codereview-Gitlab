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
        :root {{
            --primary-color: #4A90E2;
            --secondary-color: #5DADE2;
            --accent-color: #85C1E9;
            --light-color: #D6EAF8;
            --dark-color: #2C3E50;
            --success-color: #58D68D;
            --warning-color: #F8C471;
            --danger-color: #EC7063;
            --text-color: #2C3E50;
            --border-radius: 12px;
            --box-shadow: 0 6px 15px rgba(0, 0, 0, 0.1);
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            padding: 20px;
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            background-attachment: fixed;
            color: var(--text-color);
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
        }}
        
        .header {{
            background: linear-gradient(120deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            border-radius: var(--border-radius);
            padding: 30px;
            margin-bottom: 25px;
            box-shadow: var(--box-shadow);
            color: white;
            text-align: center;
            animation: fadeInDown 0.8s ease-out;
        }}
        
        .header h1 {{
            font-weight: 700;
            margin-bottom: 10px;
            text-shadow: 1px 1px 3px rgba(0, 0, 0, 0.2);
            font-size: 2.5rem;
        }}
        
        .header .lead {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}
        
        .content {{
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: var(--border-radius);
            padding: 30px;
            box-shadow: 0 6px 15px rgba(0, 0, 0, 0.08);
            backdrop-filter: blur(10px);
            animation: fadeInUp 0.8s ease-out;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: var(--dark-color);
            font-size: 0.95em;
            padding: 20px;
            background-color: rgba(255, 255, 255, 0.7);
            border-radius: 8px;
            animation: fadeIn 1s ease-out;
        }}
        
        h1, h2, h3 {{
            color: var(--dark-color);
            margin-top: 1.5rem;
            margin-bottom: 1rem;
            font-weight: 600;
        }}
        
        h1 {{
            border-bottom: 3px solid var(--accent-color);
            padding-bottom: 10px;
            position: relative;
        }}
        
        h1:after {{
            content: "";
            position: absolute;
            bottom: -3px;
            left: 0;
            width: 100px;
            height: 3px;
            background: linear-gradient(90deg, var(--accent-color), transparent);
        }}
        
        h2 {{
            border-bottom: 2px solid var(--light-color);
            padding-bottom: 8px;
            position: relative;
        }}
        
        h2:after {{
            content: "";
            position: absolute;
            bottom: -2px;
            left: 0;
            width: 60px;
            height: 2px;
            background: linear-gradient(90deg, var(--light-color), transparent);
        }}
        
        .author-section {{
            border-left: 5px solid var(--primary-color);
            padding: 20px;
            margin: 25px 0;
            background-color: rgba(214, 234, 248, 0.3);
            border-radius: 0 8px 8px 0;
        }}
        
        code {{
            background-color: var(--light-color);
            padding: 3px 6px;
            border-radius: 4px;
            font-size: 0.95em;
            color: var(--dark-color);
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        }}
        
        pre {{
            background-color: #f8f9fa;
            border: 1px solid var(--light-color);
            border-radius: 8px;
            padding: 15px;
            overflow-x: auto;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
            font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
        }}
        
        /* 表格样式改进 */
        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            margin: 20px 0;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
            background-color: white;
            animation: fadeIn 0.5s ease-out;
        }}
        
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid var(--light-color);
        }}
        
        th {{
            background: linear-gradient(120deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            position: relative;
            overflow: hidden;
        }}
        
        th:after {{
            content: "";
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }}
        
        th:hover:after {{
            left: 100%;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        tr:nth-child(even) {{
            background-color: rgba(214, 234, 248, 0.2);
        }}
        
        tr:hover {{
            background-color: rgba(133, 193, 233, 0.3);
            transition: background-color 0.3s;
            transform: scale(1.01);
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
        }}
        
        td:first-child, th:first-child {{
            border-left: none;
        }}
        
        td:last-child, th:last-child {{
            border-right: none;
        }}
        
        /* 链接样式 */
        a {{
            color: var(--primary-color);
            text-decoration: none;
            font-weight: 500;
            position: relative;
            transition: color 0.3s;
        }}
        
        a:hover {{
            color: var(--secondary-color);
            text-decoration: underline;
        }}
        
        a:before {{
            content: "";
            position: absolute;
            width: 0;
            height: 2px;
            bottom: -2px;
            left: 0;
            background-color: var(--secondary-color);
            transition: width 0.3s;
        }}
        
        a:hover:before {{
            width: 100%;
        }}
        
        /* 列表样式 */
        ul, ol {{
            padding-left: 25px;
        }}
        
        li {{
            margin: 10px 0;
            position: relative;
            padding-left: 15px;
        }}
        
        ul li:before {{
            content: "•";
            color: var(--primary-color);
            position: absolute;
            left: 0;
            font-weight: bold;
        }}
        
        /* 卡片样式 */
        .card {{
            border: none;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
            margin-bottom: 20px;
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
        }}
        
        .card-header {{
            background: linear-gradient(120deg, var(--light-color) 0%, #EBF5FB 100%);
            border-bottom: none;
            font-weight: 600;
            border-radius: 10px 10px 0 0 !important;
        }}
        
        /* 响应式设计 */
        @media (max-width: 768px) {{
            .header {{
                padding: 20px;
            }}
            
            .content {{
                padding: 20px;
            }}
            
            th, td {{
                padding: 12px 10px;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
        }}
        
        /* 动画效果 */
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        @keyframes fadeInDown {{
            from {{
                opacity: 0;
                transform: translateY(-20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="display-4">代码审查报告</h1>
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
        # 确保目录存在
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
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