# agents/administrative_agent.py
from utils.llm_utils import llm_utils
from knowledge_base.rag_manager import RAGManager
import logging

logger = logging.getLogger(__name__)


class AdministrativeAgent:
    """行政事务智能体：负责奖学金申请、请假流程、报销规则、宿舍管理、证件办理等"""

    def __init__(self):
        self.agent_name = "AdministrativeAgent"

        self.system_prompt = """你是一个专业的校园行政事务顾问，专门回答关于奖学金、助学金、请假、报销、宿舍管理、证件办理、学籍管理等行政类问题。

【核心职责范围】：
1. 奖学金：申请条件、评选流程、金额标准、材料准备
2. 助学金：贫困认定、申请流程、发放时间
3. 请假流程：病假、事假、公假申请流程和审批权限
4. 报销事务：医保报销、活动报销、差旅报销
5. 宿舍管理：入住退宿、调宿申请、宿舍报修、违规处理
6. 证件办理：学生证、校园卡、在读证明、成绩单
7. 学籍管理：休学、复学、退学、转专业流程

【重要原则】：
- 必须使用检索到的文档信息回答
- 注意时间节点、材料清单、办理地点等细节
- 如果文档中没有相关信息，明确说明并提供咨询渠道

请用专业、耐心、清晰的语气回答。"""

        # 初始化RAG管理器
        try:
            self.rag = RAGManager()
            logger.info("AdministrativeAgent RAG初始化成功")
        except Exception as e:
            logger.error(f"AdministrativeAgent RAG初始化失败: {e}")
            self.rag = None

    def answer(self, user_query, context=None):
        """回答行政事务相关问题"""
        # 如果RAG可用，检索相关知识
        rag_context = ""
        if self.rag:
            try:
                results = self.rag.search(user_query, top_k=5)
                if results:
                    context_parts = []
                    for i, result in enumerate(results, 1):
                        source = result['metadata'].get('filename', '未知来源')
                        similarity = 1 - result.get('distance', 0)
                        context_parts.append(
                            f"【文档 {i}】来源：{source} (相关度：{similarity:.2f})\n"
                            f"内容：{result['content']}\n"
                        )
                    rag_context = "\n".join(context_parts)
                    logger.info(f"检索到 {len(results)} 个相关文档片段")
            except Exception as e:
                logger.error(f"RAG检索失败: {e}")

        if rag_context:
            enhanced_prompt = f"""学生问题：{user_query}

【校园官方文档检索结果】
{rag_context}

请根据以上信息回答，注意：
1. 引用具体的时间、金额、流程
2. 如有步骤，按顺序列出
3. 注明信息来源
4. 询问是否需要进一步帮助"""
        else:
            enhanced_prompt = f"""学生问题：{user_query}

未在校园知识库中找到相关信息。

请说明未找到相关信息，并建议查阅学生处网站或咨询辅导员。"""

        try:
            response = llm_utils.chat_with_system_prompt(
                system_prompt=self.system_prompt,
                user_message=enhanced_prompt,
                temperature=0.2
            )
            return response
        except Exception as e:
            logger.error(f"AdministrativeAgent回答失败: {e}")
            return f"抱歉，我遇到了技术问题: {str(e)}"


# 测试代码
if __name__ == "__main__":
    agent = AdministrativeAgent()
    test_queries = [
        "怎么申请国家奖学金？",
        "请假需要什么手续？",
        "宿舍怎么报修？"
    ]
    for query in test_queries:
        print(f"\n📝 问题: {query}")
        print(f"💡 回答: {agent.answer(query)}")