# knowledge_base/rag_manager.py
import os
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

# 向量数据库
import chromadb
from chromadb.config import Settings

# 文本处理
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader
)

# 嵌入模型 - 使用本地模型，不需要API
from sentence_transformers import SentenceTransformer

from config import config

logger = logging.getLogger(__name__)


class RAGManager:
    """RAG知识库管理器"""

    def __init__(self, collection_name="campus_docs"):
        """
        初始化RAG管理器

        Args:
            collection_name: ChromaDB集合名称
        """
        self.collection_name = collection_name
        self.persist_directory = config.VECTOR_DB_PATH

        # 初始化嵌入模型（使用本地模型，免费）
        logger.info("正在加载嵌入模型...")
        self.embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        logger.info("嵌入模型加载完成")

        # 初始化ChromaDB客户端
        self._init_chroma_client()

        # 初始化文本分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # 每个块的大小
            chunk_overlap=100,  # 块之间的重叠，保持上下文连贯
            length_function=len,
            separators=["\n\n", "\n", "。", "，", " ", ""]
        )

    def _init_chroma_client(self):
        """初始化ChromaDB客户端"""
        # 确保持久化目录存在
        os.makedirs(self.persist_directory, exist_ok=True)

        # 创建客户端
        self.client = chromadb.PersistentClient(
            path=self.persist_directory
        )

        # 获取或创建集合
        try:
            self.collection = self.client.get_collection(self.collection_name)
            logger.info(f"加载现有集合: {self.collection_name}")
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
            )
            logger.info(f"创建新集合: {self.collection_name}")

    def load_documents(self, file_paths: List[str]) -> List[Dict]:
        """
        加载文档文件

        Args:
            file_paths: 文件路径列表

        Returns:
            List[Dict]: 文档列表，每个文档包含内容和元数据
        """
        documents = []

        for file_path in file_paths:
            try:
                path = Path(file_path)
                if not path.exists():
                    logger.warning(f"文件不存在: {file_path}")
                    continue

                logger.info(f"正在加载: {file_path}")

                # 根据文件扩展名选择加载器
                if path.suffix.lower() == '.pdf':
                    loader = PyPDFLoader(str(path))
                elif path.suffix.lower() == '.txt':
                    loader = TextLoader(str(path), encoding='utf-8')
                elif path.suffix.lower() in ['.docx', '.doc']:
                    loader = Docx2txtLoader(str(path))
                else:
                    logger.warning(f"不支持的文件类型: {path.suffix}")
                    continue

                # 加载文档
                docs = loader.load()

                # 添加元数据
                for doc in docs:
                    doc.metadata['source'] = str(path)
                    doc.metadata['filename'] = path.name

                documents.extend(docs)
                logger.info(f"成功加载 {len(docs)} 个页面从 {path.name}")

            except Exception as e:
                logger.error(f"加载文件 {file_path} 失败: {e}")

        return documents

    def process_and_index(self, documents: List, batch_size: int = 32):
        """
        处理文档并建立索引

        Args:
            documents: 文档列表
            batch_size: 批处理大小
        """
        if not documents:
            logger.warning("没有文档需要处理")
            return

        # 分割文档
        logger.info("正在分割文档...")
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"分割成 {len(chunks)} 个文本块")

        # 准备批量添加
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            ids = []
            texts = []
            metadatas = []

            for j, chunk in enumerate(batch):
                # 生成唯一ID
                chunk_id = f"doc_{i + j}_{hash(chunk.page_content) % 10000}"

                ids.append(chunk_id)
                texts.append(chunk.page_content)
                metadatas.append(chunk.metadata)

            # 计算嵌入向量
            logger.info(f"正在计算第 {i // batch_size + 1}/{(len(chunks) - 1) // batch_size + 1} 批的嵌入向量...")
            embeddings = self.embedding_model.encode(texts).tolist()

            # 添加到ChromaDB
            self.collection.add(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas
            )

            logger.info(f"已添加第 {i // batch_size + 1} 批，共 {len(batch)} 个文本块")

        logger.info(f"索引完成！总计 {len(chunks)} 个文本块")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        搜索相关文档

        Args:
            query: 查询文本
            top_k: 返回的最相关文档数量

        Returns:
            List[Dict]: 相关文档列表
        """
        # 计算查询的嵌入向量
        query_embedding = self.embedding_model.encode(query).tolist()

        # 搜索
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        # 格式化结果
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else None
                })

        return formatted_results

    def get_relevant_context(self, query: str, top_k: int = 3) -> str:
        """
        获取与查询相关的上下文文本

        Args:
            query: 查询文本
            top_k: 返回的文档数量

        Returns:
            str: 合并后的上下文文本
        """
        results = self.search(query, top_k)

        if not results:
            return ""

        # 构建上下文
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result['metadata'].get('filename', '未知来源')
            context_parts.append(f"[{i}] 来自 {source}:\n{result['content']}\n")

        return "\n".join(context_parts)

    def index_folder(self, folder_path: str):
        """
        索引整个文件夹中的所有支持文档

        Args:
            folder_path: 文件夹路径
        """
        folder = Path(folder_path)
        if not folder.exists():
            logger.error(f"文件夹不存在: {folder_path}")
            return

        # 支持的文件扩展名
        supported_exts = ['.pdf', '.txt', '.docx', '.doc']

        # 收集所有文件
        files = []
        for ext in supported_exts:
            files.extend(folder.glob(f"**/*{ext}"))

        if not files:
            logger.warning(f"文件夹中没有支持的文档: {folder_path}")
            return

        logger.info(f"找到 {len(files)} 个文档")

        # 加载所有文档
        all_docs = []
        for file in files:
            docs = self.load_documents([str(file)])
            all_docs.extend(docs)

        # 建立索引
        self.process_and_index(all_docs)

    def get_stats(self) -> Dict:
        """获取知识库统计信息"""
        count = self.collection.count()
        return {
            'collection_name': self.collection_name,
            'document_count': count,
            'persist_directory': self.persist_directory
        }


# 测试代码
if __name__ == "__main__":
    # 初始化RAG管理器
    rag = RAGManager()

    # 测试搜索（需要先有索引）
    test_query = "计算机专业培养方案"
    context = rag.get_relevant_context(test_query)
    print(f"查询: {test_query}")
    print(f"相关上下文:\n{context}")