# update_knowledge_base.py
import os
import sys
from pathlib import Path
import logging
from knowledge_base.rag_manager import RAGManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_knowledge_base():
    """自动索引data文件夹中的所有新文档"""

    print("=" * 60)
    print("📚 CampusMind 知识库更新工具")
    print("=" * 60)

    # 检查data文件夹
    data_path = Path("./data")
    if not data_path.exists():
        print("❌ data文件夹不存在，正在创建...")
        data_path.mkdir(exist_ok=True)
        print(f"✅ 请在 {data_path.absolute()} 放入你的文档")
        return

    # 支持的格式
    supported_formats = ['.pdf', '.txt', '.docx', '.doc', '.md']

    # 找出所有文档
    all_files = []
    for fmt in supported_formats:
        all_files.extend(data_path.glob(f"**/*{fmt}"))

    if not all_files:
        print(f"❌ data文件夹中没有支持的文档")
        print(f"支持的格式: {supported_formats}")
        print(f"请将文档放入: {data_path.absolute()}")
        return

    print(f"\n📄 找到 {len(all_files)} 个文档:")
    for f in all_files:
        size = f.stat().st_size / 1024  # KB
        print(f"  - {f.name} ({size:.1f}KB)")

    # 询问确认
    print("\n⚠️  这将重建整个知识库索引")
    confirm = input("是否继续？(y/n): ")
    if confirm.lower() != 'y':
        print("已取消")
        return

    # 初始化RAG
    print("\n🔄 初始化RAG管理器...")
    rag = RAGManager()

    # 批量索引
    print("\n📊 正在索引文档...")
    rag.index_folder(str(data_path))

    # 显示统计
    stats = rag.get_stats()
    print("\n✅ 知识库更新完成！")
    print(f"📊 统计信息:")
    print(f"  - 文档数量: {stats['document_count']}")
    print(f"  - 存储位置: {stats['persist_directory']}")

    # 测试搜索
    print("\n🔍 测试搜索效果:")
    test_queries = ["学分要求", "图书馆", "奖学金"]
    for q in test_queries:
        print(f"\n  查询: '{q}'")
        results = rag.search(q, top_k=2)
        for r in results:
            sim = 1 - r['distance']
            src = r['metadata'].get('filename', '未知')
            print(f"    - [{sim:.2f}] {src}: {r['content'][:50]}...")


if __name__ == "__main__":
    update_knowledge_base()