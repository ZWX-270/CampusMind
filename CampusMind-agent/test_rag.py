# test_rag.py
from knowledge_base.rag_manager import RAGManager


def test_rag():
    rag = RAGManager()

    test_queries = [
        "计算机专业学分",
        "图书馆开放时间",
        "奖学金申请"
    ]

    for query in test_queries:
        print(f"\n{'=' * 50}")
        print(f"查询: {query}")
        print('=' * 50)

        results = rag.search(query, top_k=2)
        for i, result in enumerate(results, 1):
            print(f"\n--- 结果 {i} (相似度: {1 - result['distance']:.3f}) ---")
            print(f"来源: {result['metadata'].get('filename', '未知')}")
            print(f"内容: {result['content'][:200]}...")


if __name__ == "__main__":
    test_rag()