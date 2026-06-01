# agents/academic_agent.py
from utils.llm_utils import llm_utils
from knowledge_base.rag_manager import RAGManager
import logging

logger = logging.getLogger(__name__)


class AcademicAgent:
    """学术咨询智能体：负责选课、培养方案、学分计算等问题"""

    def __init__(self):
        self.agent_name = "AcademicAgent"
        self.system_prompt = """你是一个专业的校园学术顾问，你的核心职责是严格基于校园官方文档回答学生问题。

【重要原则 - 必须遵守】：
1. 如果检索到的文档中有相关信息，必须使用这些信息回答，并注明来源
2. 严禁编造或使用通用知识替代官方文档中的具体信息
3. 如果文档中没有相关信息，明确说明“在现有文档中未找到相关信息”，然后才提供通用建议
4. 回答要具体、准确，引用文档中的原文

请用友好、专业的语气回答学生的问题。"""

        # 初始化RAG管理器
        try:
            self.rag = RAGManager()
            logger.info("AcademicAgent RAG初始化成功")
        except Exception as e:
            logger.error(f"AcademicAgent RAG初始化失败: {e}")
            self.rag = None

    def answer(self, user_query, context=None):
        """
        回答学术相关问题，强制优先使用RAG结果
        """
        # 如果RAG可用，检索相关知识
        rag_context = ""
        if self.rag:
            try:
                # 检索相关文档
                results = self.rag.search(user_query, top_k=3)
                if results:
                    # 格式化检索结果
                    context_parts = []
                    for i, result in enumerate(results, 1):
                        source = result['metadata'].get('filename', '未知来源')
                        similarity = result.get('distance', 0)
                        # distance越小越相似，转换为相似度分数
                        similarity_score = 1 - similarity if similarity else 0

                        context_parts.append(
                            f"【文档 {i}】来源：{source} (相关度：{similarity_score:.2f})\n"
                            f"内容：{result['content']}\n"
                        )

                    rag_context = "\n".join(context_parts)
                    logger.info(f"检索到 {len(results)} 个相关文档片段")
            except Exception as e:
                logger.error(f"RAG检索失败: {e}")

        # 构建增强的提示词
        if rag_context:
            # 有RAG结果的情况 - 强制使用
            enhanced_prompt = f"""学生问题：{user_query}

【校园官方文档检索结果】
以下是系统从校园知识库中检索到的相关文档内容，这些是回答问题的唯一依据：
{rag_context}

【回答要求 - 必须严格遵守】
1. **必须**使用上述文档中的信息回答，直接引用具体内容
2. 如果文档中有相关数据（如学分、时间、金额等），必须原样引用
3. 在回答开头注明：“根据学校规定，...”
4. 在回答末尾注明信息来源：“（信息来源：{results[0]['metadata'].get('filename', '校园文档')}）”
5. 如果文档信息不完整，说明文档中提供了哪些信息，缺少哪些信息
6. **严禁**使用通用知识替代文档中的具体规定

请严格按照要求回答："""
        else:
            # 没有RAG结果的情况
            enhanced_prompt = f"""学生问题：{user_query}

【提示】
系统在校园知识库中未找到相关文档。

【回答要求】
1. 说明“在现有校园文档中未找到相关信息”
2. 基于一般高校的通用情况提供参考信息
3. 建议用户查阅学校官方渠道获取准确信息
4. 询问是否需要帮助查找其他方面的信息

请按照要求回答："""

        try:
            response = llm_utils.chat_with_system_prompt(
                system_prompt=self.system_prompt,
                user_message=enhanced_prompt,
                temperature=0.1  # 降低温度，确保准确性
            )
            return response
        except Exception as e:
            logger.error(f"AcademicAgent回答失败: {e}")
            return f"抱歉，我遇到了技术问题: {str(e)}"


# 测试代码
if __name__ == "__main__":
    agent = AcademicAgent()
    test_queries = [
        "计算机专业需要修满多少学分才能毕业？",
        "我下学期想选人工智能导论，这门课有什么先修课要求吗？",
        "如果期末考试挂了怎么办？"
    ]

    for query in test_queries:
        print(f"\n📝 问题: {query}")
        print(f"💡 回答: {agent.answer(query)}")
        print("-" * 50)