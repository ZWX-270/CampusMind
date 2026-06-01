# utils/llm_utils.py
from openai import OpenAI
from config import config
import logging

logger = logging.getLogger(__name__)


class LLMUtils:
    def __init__(self):
        """初始化LLM客户端"""
        config.check_config()

        self.client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
            timeout=60,  # 增加超时时间
            max_retries=3  # 失败重试
        )
        self.model = config.MODEL_NAME

    def chat(self, messages, temperature=0.7, max_tokens=4000):
        """发送聊天请求"""
        try:
            logger.info(f"调用LLM，模型: {self.model}")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return f"抱歉，我遇到了一个错误: {str(e)}"

    def chat_with_system_prompt(self, system_prompt, user_message, **kwargs):
        """带系统提示词的聊天"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        return self.chat(messages, **kwargs)


# 创建全局实例
llm_utils = LLMUtils()

# 测试代码
if __name__ == "__main__":
    # 测试LLM连接
    print("测试LLM连接...")
    response = llm_utils.chat_with_system_prompt(
        "你是一个有帮助的助手。",
        "你好，请用一句话介绍自己"
    )
    print(f"回复: {response}")