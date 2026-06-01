# agents/quality_agent.py
from utils.llm_utils import llm_utils
from knowledge_base.rag_manager import RAGManager
import logging
import json
import re

logger = logging.getLogger(__name__)


class QualityAgent:
    """
    质量审核智能体：交叉验证其他智能体的回答准确性，减少幻觉

    功能：
    1. 验证回答是否与知识库一致
    2. 检测是否存在编造的信息
    3. 对回答进行可信度评分
    4. 提供修正建议
    """

    def __init__(self):
        self.agent_name = "QualityAgent"

        # 系统提示词
        self.system_prompt = """你是一个严格的质量审核专家，专门负责验证校园助手的回答准确性。

【你的职责】：
1. 对照知识库内容，检查回答中的事实是否正确
2. 识别是否存在编造或幻觉信息
3. 评估回答的可信度
4. 提供具体的修正建议

【审核维度】：
- 事实准确性：回答中的数字、时间、流程是否正确
- 信息完整性：是否遗漏重要信息
- 来源可靠性：是否引用官方文档
- 幻觉检测：是否存在知识库中没有的内容

【输出格式】：
请以JSON格式返回审核结果：
{
    "is_accurate": true/false,
    "confidence_score": 0-100,
    "hallucination_detected": true/false,
    "accurate_parts": ["正确的部分"],
    "inaccurate_parts": ["错误的部分"],
    "missing_parts": ["遗漏的重要内容"],
    "suggestions": ["修正建议"],
    "source_verified": "引用的来源是否在知识库中",
    "verdict": "通过/部分通过/不通过"
}

请严格按JSON格式输出，不要有其他文字。"""

        # 初始化RAG管理器（用于事实核查）
        try:
            self.rag = RAGManager()
            logger.info("QualityAgent RAG初始化成功")
        except Exception as e:
            logger.error(f"QualityAgent RAG初始化失败: {e}")
            self.rag = None

    def verify_answer(self, user_query: str, agent_answer: str, agent_type: str) -> dict:
        """
        验证智能体回答的准确性

        Args:
            user_query: 用户原始问题
            agent_answer: 智能体的回答
            agent_type: 智能体类型（academic/life/administrative）

        Returns:
            dict: 审核结果
        """
        logger.info(f"质量审核开始 - 问题: {user_query[:50]}...")

        # 1. 检索相关知识库内容
        rag_context = ""
        if self.rag:
            try:
                results = self.rag.search(user_query, top_k=5)
                if results:
                    context_parts = []
                    for i, result in enumerate(results, 1):
                        source = result['metadata'].get('filename', '未知来源')
                        context_parts.append(
                            f"【参考文档 {i}】来源：{source}\n"
                            f"内容：{result['content']}\n"
                        )
                    rag_context = "\n".join(context_parts)
                    logger.info(f"检索到 {len(results)} 个参考文档")
            except Exception as e:
                logger.error(f"RAG检索失败: {e}")

        # 2. 构建审核提示词
        verification_prompt = f"""【用户问题】
{user_query}

【待审核回答】（来自{agent_type}智能体）
{agent_answer}

【知识库参考内容】（用于事实核查）
{rag_context if rag_context else "未检索到相关知识库内容"}

请根据以上信息进行审核，判断回答是否准确。"""

        try:
            # 调用LLM进行审核
            response = llm_utils.chat_with_system_prompt(
                system_prompt=self.system_prompt,
                user_message=verification_prompt,
                temperature=0.1  # 审核需要低温度，确保一致性
            )

            # 解析JSON结果
            result = self._parse_json_response(response)

            # 添加额外信息
            result['agent_type'] = agent_type
            result['user_query'] = user_query
            result['verified_answer'] = agent_answer

            logger.info(f"审核结果: 准确={result['is_accurate']}, 置信度={result['confidence_score']}")
            return result

        except Exception as e:
            logger.error(f"审核失败: {e}")
            return {
                "is_accurate": False,
                "confidence_score": 0,
                "hallucination_detected": True,
                "accurate_parts": [],
                "inaccurate_parts": ["审核过程出错"],
                "missing_parts": [],
                "suggestions": ["请检查系统配置"],
                "source_verified": "审核失败",
                "verdict": "不通过",
                "error": str(e)
            }

    def _parse_json_response(self, response: str) -> dict:
        """解析LLM返回的JSON响应"""
        try:
            # 清理响应
            response = response.strip()
            # 移除可能的markdown代码块
            response = re.sub(r'^```json\s*', '', response)
            response = re.sub(r'^```\s*', '', response)
            response = re.sub(r'\s*```$', '', response)

            result = json.loads(response)
            return result
        except json.JSONDecodeError:
            # 如果解析失败，返回默认值
            return {
                "is_accurate": False,
                "confidence_score": 50,
                "hallucination_detected": True,
                "accurate_parts": [],
                "inaccurate_parts": ["无法解析审核结果"],
                "missing_parts": [],
                "suggestions": ["请重新提问"],
                "source_verified": "解析失败",
                "verdict": "不通过"
            }

    def quick_check(self, user_query: str, agent_answer: str) -> tuple:
        """
        快速检查：返回是否通过和置信度

        Returns:
            tuple: (is_passed, confidence, feedback)
        """
        result = self.verify_answer(user_query, agent_answer, "unknown")

        is_passed = result.get('is_accurate', False) and result.get('confidence_score', 0) > 70

        feedback = ""
        if is_passed:
            feedback = "✅ 回答准确，通过审核"
        elif result.get('hallucination_detected', False):
            feedback = "⚠️ 检测到可能的不准确信息，建议核实"
        else:
            feedback = "❌ 回答存在不准确内容，请参考修正建议"

        return is_passed, result.get('confidence_score', 0), feedback, result

    def generate_corrected_answer(self, user_query: str, original_answer: str, verification_result: dict) -> str:
        """
        基于审核结果生成修正后的回答

        Args:
            user_query: 用户问题
            original_answer: 原始回答
            verification_result: 审核结果

        Returns:
            str: 修正后的回答
        """
        if verification_result.get('is_accurate', False) and verification_result.get('confidence_score', 0) > 80:
            return original_answer

        # 构建修正提示词
        correction_prompt = f"""【用户问题】
{user_query}

【原始回答】
{original_answer}

【审核发现的问题】
- 不准确的部分: {verification_result.get('inaccurate_parts', [])}
- 遗漏的内容: {verification_result.get('missing_parts', [])}
- 修正建议: {verification_result.get('suggestions', [])}

请根据审核结果，生成一个修正后的回答。要求：
1. 修正所有不准确的信息
2. 补充遗漏的重要内容
3. 保持回答清晰、友好
4. 在开头注明"（经质量审核修正）"

请直接输出修正后的回答，不要有其他格式。"""

        try:
            system_prompt = "你是一个专业的回答修正助手，负责根据审核意见改进回答质量。"
            corrected = llm_utils.chat_with_system_prompt(
                system_prompt=system_prompt,
                user_message=correction_prompt,
                temperature=0.3
            )
            return corrected
        except Exception as e:
            logger.error(f"生成修正回答失败: {e}")
            return original_answer + "\n\n⚠️ 提示：以上回答可能需要核实，建议查阅官方渠道获取准确信息。"


# 质量审核装饰器（可选，用于自动审核）
def require_quality_check(agent_func):
    """
    装饰器：自动对智能体回答进行质量审核
    """

    def wrapper(self, user_query, *args, **kwargs):
        # 获取原始回答
        original_answer = agent_func(self, user_query, *args, **kwargs)

        # 进行质量审核
        quality_agent = QualityAgent()
        is_passed, confidence, feedback, result = quality_agent.quick_check(user_query, original_answer)

        # 如果置信度低于70，尝试修正
        if confidence < 70:
            corrected = quality_agent.generate_corrected_answer(user_query, original_answer, result)
            return corrected + f"\n\n---\n*[质量审核: {feedback} | 置信度: {confidence}%]*"

        return original_answer + f"\n\n---\n*[质量审核: {feedback} | 置信度: {confidence}%]*"

    return wrapper


# 测试代码
if __name__ == "__main__":
    print("=" * 50)
    print("质量审核智能体测试")
    print("=" * 50)

    quality = QualityAgent()

    # 测试用例
    test_cases = [
        {
            "query": "国家奖学金多少钱？",
            "answer": "国家奖学金是8000元。",
            "expected": "应该通过"
        },
        {
            "query": "国家奖学金多少钱？",
            "answer": "国家奖学金是5000元。",
            "expected": "应该不通过（数字错误）"
        },
        {
            "query": "图书馆几点关门？",
            "answer": "图书馆晚上10点关门。",
            "expected": "需要验证"
        }
    ]

    for test in test_cases:
        print(f"\n📝 问题: {test['query']}")
        print(f"💬 回答: {test['answer']}")

        result = quality.verify_answer(test['query'], test['answer'], "test")
        print(f"📊 审核结果:")
        print(f"   - 准确: {result.get('is_accurate')}")
        print(f"   - 置信度: {result.get('confidence_score')}%")
        print(f"   - 幻觉检测: {result.get('hallucination_detected')}")
        print(f"   - 判定: {result.get('verdict')}")