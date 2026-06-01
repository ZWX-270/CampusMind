# knowledge_base/build_knowledge_base.py
import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from knowledge_base.rag_manager import RAGManager
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_knowledge_base(data_folder: str = "./data"):
    """
    构建知识库索引

    Args:
        data_folder: 存放原始文档的文件夹
    """
    logger.info("=" * 50)
    logger.info("开始构建知识库")
    logger.info("=" * 50)

    # 确保data文件夹存在
    data_path = Path(data_folder)
    data_path.mkdir(exist_ok=True)

    # 检查是否有文档
    files = list(data_path.glob("**/*"))
    supported_exts = ['.pdf', '.txt', '.docx', '.doc']
    doc_files = [f for f in files if f.suffix.lower() in supported_exts]

    if not doc_files:
        logger.warning(f"在 {data_folder} 中没有找到支持的文档")
        logger.info("请将以下类型的文档放入data文件夹：")
        for ext in supported_exts:
            logger.info(f"  - *{ext}")
        return

    logger.info(f"找到 {len(doc_files)} 个文档:")
    for f in doc_files:
        logger.info(f"  - {f.name}")

    # 初始化RAG管理器
    rag = RAGManager()

    # 索引所有文档
    rag.index_folder(data_folder)

    # 显示统计信息
    stats = rag.get_stats()
    logger.info("=" * 50)
    logger.info("知识库构建完成！")
    logger.info(f"集合名称: {stats['collection_name']}")
    logger.info(f"文档数量: {stats['document_count']}")
    logger.info(f"存储位置: {stats['persist_directory']}")
    logger.info("=" * 50)

    # 测试搜索
    test_queries = [
        "计算机专业学分要求",
        "图书馆开放时间",
        "奖学金申请条件"
    ]

    logger.info("\n测试搜索效果：")
    for query in test_queries:
        context = rag.get_relevant_context(query, top_k=2)
        logger.info(f"\n查询: {query}")
        logger.info(f"找到 {len(context.split('[')) - 1} 个相关片段")
        if context:
            logger.info(f"第一个片段: {context[:200]}...")


if __name__ == "__main__":
    build_knowledge_base()