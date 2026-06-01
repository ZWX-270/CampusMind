# agents/life_agent.py
from utils.llm_utils import llm_utils
from knowledge_base.rag_manager import RAGManager
import logging

logger = logging.getLogger(__name__)


class LifeAgent:
    """生活服务智能体：提供食堂、图书馆、校园地图等信息"""

    def __init__(self):
        self.agent_name = "LifeAgent"
        self.system_prompt = """你是一个贴心的校园生活助手，严格基于校园官方文档回答关于食堂、图书馆、校园设施等问题。

【重要原则 - 必须遵守】：
1. 如果检索到的文档中有相关信息，必须使用这些信息回答，并注明来源
2. 严禁编造或使用通用知识替代官方文档中的具体信息
3. 如果文档中没有相关信息，明确说明“在现有文档中未找到相关信息”
4. 提供具体的操作指引和时间信息

请用热情、友好的语气帮助学生解决生活中的问题。"""

        # 初始化RAG管理器
        try:
            self.rag = RAGManager()
            logger.info("LifeAgent RAG初始化成功")
        except Exception as e:
            logger.error(f"LifeAgent RAG初始化失败: {e}")
            self.rag = None

    def answer(self, user_query, context=None):
        """回答生活服务相关问题，强制使用RAG结果"""
        # 如果RAG可用，检索相关知识
        rag_context = ""
        if self.rag:
            try:
                results = self.rag.search(user_query, top_k=3)
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
以下是系统从校园知识库中检索到的相关文档内容：
{rag_context}

【回答要求】
1. **必须**使用上述文档信息回答
2. 直接引用具体时间、地点、规则
3. 在回答开头注明：“根据学校规定，...”
4. 在回答末尾注明信息来源
5. 可以加上温馨提示（如高峰期、预约方式等）

请严格按照要求回答："""
        else:
            enhanced_prompt = f"""学生问题：{user_query}

【提示】未在校园知识库中找到相关信息。

请说明未找到相关信息，并提供一般性建议，同时建议查阅校园通知。"""

        try:
            response = llm_utils.chat_with_system_prompt(
                system_prompt=self.system_prompt,
                user_message=enhanced_prompt,
                temperature=0.2
            )
            return response
        except Exception as e:
            logger.error(f"LifeAgent回答失败: {e}")
            return f"抱歉，我遇到了技术问题: {str(e)}"


# 测试代码
if __name__ == "__main__":
    agent = LifeAgent()
    test_queries = [
        "图书馆周末开门吗？",
        "第一食堂有什么好吃的推荐？",
        "校园卡丢了怎么办？"
    ]

    for query in test_queries:
        print(f"\n📝 问题: {query}")
        print(f"💡 回答: {agent.answer(query)}")
        print("-" * 50)