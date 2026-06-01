# agents/navigation_agent.py
from utils.llm_utils import llm_utils
import json
import logging
import re

logger = logging.getLogger(__name__)


class NavigationAgent:
    """导航智能体：识别用户意图并路由到对应专业智能体"""

    def __init__(self):
        self.agent_name = "NavigationAgent"
        # 定义可路由的目标智能体
        self.target_agents = {
            "academic": "学术咨询智能体 - 负责选课、培养方案、学分计算、考试安排、课程查询等问题",
            "life": "生活服务智能体 - 负责食堂菜单、图书馆座位、校园地图、校园活动、设施开放时间等信息",
            "administrative": "行政事务智能体 - 负责奖学金申请、请假流程、报销规则、证件办理、宿舍管理、学籍变动等问题",
            "general": "通用对话智能体 - 处理一般性问题、闲聊、非校园相关咨询"
        }

    def analyze_intent(self, user_query):
        """
        分析用户意图，返回路由目标
        """
        system_prompt = f"""你是一个校园服务导航员。请分析用户问题的意图，将其路由到最合适的智能体。

可路由的智能体：
{json.dumps(self.target_agents, ensure_ascii=False, indent=2)}

分析规则：
1. academic: 包含"选课"、"学分"、"培养方案"、"课程"、"考试"、"专业"、"教务处"等关键词
2. life: 包含"食堂"、"图书馆"、"座位"、"地图"、"开门"、"关门"、"活动"等关键词
3. administrative: 包含"奖学金"、"请假"、"报销"、"申请"、"办理"、"宿舍"等关键词
4. general: 其他问题或寒暄

请以JSON格式返回分析结果，包含以下字段：
- intent: 目标智能体名称 (academic/life/administrative/general)
- confidence: 置信度 (0-1之间的小数)
- reasoning: 推理理由
- keywords: 从问题中提取的关键词列表

只返回JSON，不要有其他文字。"""

        try:
            response = llm_utils.chat_with_system_prompt(
                system_prompt=system_prompt,
                user_message=user_query,
                temperature=0.1
            )

            # 清理响应，提取JSON
            response = response.strip()
            # 移除可能的markdown代码块标记
            response = re.sub(r'^```json\s*', '', response)
            response = re.sub(r'^```\s*', '', response)
            response = re.sub(r'\s*```$', '', response)

            result = json.loads(response.strip())
            logger.info(f"意图分析结果: {result}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 响应: {response}")
            return self._fallback_analysis(user_query)
        except Exception as e:
            logger.error(f"意图分析失败: {e}")
            return self._fallback_analysis(user_query)

    def _fallback_analysis(self, user_query):
        """后备分析：简单的关键词匹配"""
        user_query = user_query.lower()

        # 关键词映射
        keywords_map = {
            "academic": ["选课", "课程", "学分", "培养方案", "考试", "专业", "教务处", "教学", "老师", "教室"],
            "life": ["食堂", "图书馆", "餐厅", "吃饭", "座位", "地图", "开门", "关门", "活动", "超市", "校园卡"],
            "administrative": ["奖学金", "助学金", "请假", "报销", "申请", "办理", "宿舍", "入住", "退宿",
                               "证件", "补办", "休学", "复学", "转专业", "学生证", "医保", "贫困认定",
                               "调宿", "报修", "旷课", "处分", "入党", "评优"]
        }

        for intent, keywords in keywords_map.items():
            for keyword in keywords:
                if keyword in user_query:
                    return {
                        "intent": intent,
                        "confidence": 0.6,
                        "reasoning": f"通过关键词'{keyword}'匹配到{intent}类别",
                        "keywords": [keyword]
                    }

        return {
            "intent": "general",
            "confidence": 0.8,
            "reasoning": "未匹配到特定领域关键词，使用通用处理",
            "keywords": []
        }

    def route(self, user_query):
        """
        路由用户请求到对应智能体

        Returns:
            tuple: (target_agent_name, analysis_result)
        """
        analysis = self.analyze_intent(user_query)
        return analysis.get("intent", "general"), analysis


# 测试代码
if __name__ == "__main__":
    navigator = NavigationAgent()

    test_queries = [
        "我想知道计算机专业下学期的选修课有哪些",
        "图书馆今天几点关门？",
        "怎么申请国家奖学金？",
        "你好，今天天气怎么样",
        "宿舍怎么办理入住"
    ]

    for query in test_queries:
        print(f"\n📝 用户: {query}")
        intent, analysis = navigator.route(query)
        print(f"🎯 路由到: {intent}")
        print(f"📊 分析详情: {json.dumps(analysis, ensure_ascii=False, indent=2)}")