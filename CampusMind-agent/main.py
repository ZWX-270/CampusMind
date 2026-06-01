# main.py
from agents.navigation_agent import NavigationAgent
from agents.academic_agent import AcademicAgent
from agents.life_agent import LifeAgent
from agents.administrative_agent import AdministrativeAgent
from agents.quality_agent import QualityAgent

import logging
import os
import json
from datetime import datetime

try:
    from colorama import init, Fore, Style

    init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False


    class Fore:
        CYAN = '';
        YELLOW = '';
        GREEN = '';
        WHITE = '';
        MAGENTA = '';
        RED = ''


    class Style:
        RESET_ALL = ''

logger = logging.getLogger(__name__)


class CampusMind:
    """CampusMind主协调器"""

    def __init__(self):
        logger.info("正在初始化CampusMind...")

        # 初始化所有智能体
        self.navigator = NavigationAgent()
        self.academic_agent = AcademicAgent()
        self.life_agent = LifeAgent()
        self.administrative_agent = AdministrativeAgent()  # 新增
        self.quality_agent = QualityAgent()  # 新增：质量审核智能体

        # 智能体映射表（更新）
        self.agents = {
            "academic": self.academic_agent,
            "life": self.life_agent,
            "administrative": self.administrative_agent,  # 新增
            "general": self._general_response
        }

        # 配置：是否启用质量审核（可在配置中开关）
        self.enable_quality_check = True

        # 对话历史
        self.conversation_history = []

        logger.info("CampusMind初始化完成！")

    def _general_response(self, user_query, context=None):
        """通用响应函数"""
        from utils.llm_utils import llm_utils

        system_prompt = """你是一个友好的校园助手。虽然这个问题不在我的专业范围内，但我还是会尽力帮助你。
如果你有关于选课、校园生活、行政事务的具体问题，请告诉我，我可以帮你联系更专业的助手。

你可以：
- 回答一般性的问候和寒暄
- 介绍CampusMind的功能
- 引导学生提出具体问题"""

        return llm_utils.chat_with_system_prompt(
            system_prompt=system_prompt,
            user_message=user_query,
            temperature=0.7
        )

    def process_query(self, user_query):
        """
        处理用户查询的主流程
        """
        logger.info(f"收到用户查询: {user_query}")

        # 保存到对话历史
        self.conversation_history.append({
            "role": "user",
            "content": user_query,
            "time": datetime.now().isoformat()
        })

        # Step 1: 导航智能体分析意图
        target_agent, analysis = self.navigator.route(user_query)
        logger.info(f"意图分析结果: {json.dumps(analysis, ensure_ascii=False)}")

        # Step 2: 获取对应的智能体
        agent = self.agents.get(target_agent, self.agents["general"])

        # Step 3: 获取原始回答
        if target_agent in ["academic", "life", "administrative"]:
            original_response = agent.answer(user_query, None)
        else:
            original_response = agent(user_query, None)

        # Step 4: 质量审核（如果启用）
        if self.enable_quality_check:
            logger.info(f"开始质量审核 - 智能体: {target_agent}")

            # 进行审核
            is_passed, confidence, feedback, verification = self.quality_agent.quick_check(
                user_query, original_response
            )

            logger.info(f"审核结果: 通过={is_passed}, 置信度={confidence}%")

            # 如果置信度低于70，尝试修正回答
            if confidence < 70:
                logger.info("置信度较低，生成修正回答...")
                final_response = self.quality_agent.generate_corrected_answer(
                    user_query, original_response, verification
                )
                # 添加审核说明
                final_response += f"\n\n---\n🔍 *质量审核: {feedback} | 置信度: {confidence}%*"
            else:
                final_response = original_response
                # 即使通过也添加审核标记（可选）
                if confidence < 90:
                    final_response += f"\n\n---\n✅ *质量审核通过 | 置信度: {confidence}%*"
        else:
            final_response = original_response

        # 保存回答到历史
        self.conversation_history.append({
            "role": "assistant",
            "content": final_response,
            "agent": target_agent,
            "quality_checked": self.enable_quality_check,
            "time": datetime.now().isoformat()
        })

        return final_response

    def print_colored(self, text, color=Fore.WHITE, end='\n'):
        """打印彩色文本"""
        if HAS_COLORAMA:
            print(color + text + Style.RESET_ALL, end=end)
        else:
            print(text, end=end)

    def chat(self):
        """交互式聊天循环"""
        self.print_colored("=" * 60, Fore.CYAN)
        self.print_colored("欢迎使用 CampusMind - 智能校园知识服务平台", Fore.YELLOW)
        self.print_colored("=" * 60, Fore.CYAN)
        self.print_colored("\n我可以帮你解答：", Fore.GREEN)
        self.print_colored("  📚 学术问题 - 选课、学分、培养方案", Fore.GREEN)
        self.print_colored("  🍽️ 生活问题 - 食堂、图书馆、校园设施", Fore.GREEN)
        self.print_colored("  📋 行政事务 - 奖学金、请假、宿舍、报销", Fore.GREEN)
        self.print_colored("  🔍 质量审核 - 自动验证回答准确性", Fore.GREEN)
        self.print_colored("\n输入 'quit' 退出，'clear' 清屏，'history' 查看对话历史。")
        self.print_colored("输入 'toggle_qa' 开关质量审核功能。\n", Fore.GREEN)

        while True:
            try:
                self.print_colored("\n👤 你: ", Fore.WHITE, end='')
                user_input = input().strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    self.print_colored("\n👋 感谢使用 CampusMind，再见！", Fore.YELLOW)
                    break

                if user_input.lower() == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                    continue

                if user_input.lower() == 'history':
                    self._show_history()
                    continue

                if user_input.lower() == 'toggle_qa':
                    self.enable_quality_check = not self.enable_quality_check
                    status = "开启" if self.enable_quality_check else "关闭"
                    self.print_colored(f"\n🔍 质量审核已{status}", Fore.CYAN)
                    continue

                if not user_input:
                    continue

                # 处理查询
                self.print_colored("\n🤖 CampusMind思考中...", Fore.CYAN)
                response = self.process_query(user_input)

                # 输出回答
                self.print_colored(f"\n🤖 CampusMind: {response}", Fore.MAGENTA)

            except KeyboardInterrupt:
                self.print_colored("\n\n👋 检测到中断，再见！", Fore.YELLOW)
                break
            except Exception as e:
                logger.error(f"处理过程中出错: {e}")
                self.print_colored(f"\n❌ 抱歉，系统出现错误: {str(e)}", Fore.RED)

    def _show_history(self):
        """显示对话历史"""
        self.print_colored("\n📜 对话历史:", Fore.CYAN)
        for msg in self.conversation_history[-10:]:
            role = "👤 用户" if msg['role'] == 'user' else f"🤖 {msg.get('agent', 'CampusMind')}"
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            self.print_colored(f"{role}: {content}", Fore.WHITE)
            if msg.get('quality_checked'):
                self.print_colored(f"   [已质量审核]", Fore.GREEN)


if __name__ == "__main__":
    campus = CampusMind()
    campus.chat()