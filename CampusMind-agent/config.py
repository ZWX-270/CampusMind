# config.py
import os
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


class Config:
    # 模型配置 - 使用DeepSeek（免费）
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-chat")

    # 向量数据库配置
    VECTOR_DB_PATH = os.getenv("VECTOR_DB_PATH", "./data/chroma_db")

    # 智能体配置
    TEMPERATURE = 0.7
    MAX_TOKENS = 4000  # DeepSeek上下文较大，可以设大一点

    # 检查必要配置
    @classmethod
    def check_config(cls):
        if not cls.DEEPSEEK_API_KEY:
            raise ValueError(
                "请设置DEEPSEEK_API_KEY环境变量！\n"
                "1. 访问 https://platform.deepseek.com/ 注册账号\n"
                "2. 在API Keys页面创建新的API Key\n"
                "3. 将密钥填入.env文件"
            )
        return True


# 实例化配置
config = Config()