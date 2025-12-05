from biz.llm.factory import Factory


class Reporter:
    def __init__(self):
        self.client = Factory().getClient()

    def generate_report(self, data: str) -> str:
        # 根据data生成报告
        return self.client.completions(
            messages=[
                  {"role": "system", "content": "你是一位严苛的代码审查者，负责根据今日评审结果编写工作日报，你需要为每一个员工（author）的评审结果（review_result）对他们的问题情况进行汇总。"}, 
                {"role": "user", "content": f"{data} \n---\n请按员工的名字（author)分别生成今天日报。特别要求:以Markdown格式返回，不要回答其他内容。"},
            ],
        )
