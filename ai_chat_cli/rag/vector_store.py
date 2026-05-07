# -*- coding: utf-8 -*-

"""
向量存储
基于 ChromaDB 的本地向量数据库封装，支持多主题集合管理、文档入库和相似度检索
"""

import os
import uuid


# 集合名前缀，避免与 ChromaDB 内部集合冲突
_COLLECTION_PREFIX = "kb_"
# 默认主题名
DEFAULT_TOPIC = "default"


class VectorStore:
    """ChromaDB 向量存储封装，支持多主题（每个主题对应一个独立集合）"""

    def __init__(self, persist_dir):
        """
        初始化向量存储

        Args:
            persist_dir: 持久化存储目录（如 ~/.ai-chat-cli/knowledge_base/）
        """
        try:
            import chromadb
        except ImportError:
            raise ImportError(
                "RAG 功能需要 chromadb 库，请运行: pip install chromadb"
            )

        os.makedirs(persist_dir, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_dir)

    def _get_collection(self, topic=None):
        """
        获取或创建指定主题的集合

        Args:
            topic: 主题名称，默认为 "default"

        Returns:
            chromadb.Collection: 集合对象
        """
        topic = topic or DEFAULT_TOPIC
        collection_name = f"{_COLLECTION_PREFIX}{topic}"
        return self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_documents(self, documents, topic=None):
        """
        将 Document 列表添加到指定主题的向量库

        Args:
            documents: Document 列表（来自 TextSplitter 的切分结果）
            topic: 主题名称，默认为 "default"

        Returns:
            int: 成功添加的文档数量
        """
        if not documents:
            return 0

        collection = self._get_collection(topic)

        ids = []
        contents = []
        metadatas = []

        for doc in documents:
            doc_id = uuid.uuid4().hex
            ids.append(doc_id)
            contents.append(doc.content)
            # ChromaDB metadata 值必须是 str/int/float/bool
            meta = {
                k: str(v) if not isinstance(v, (str, int, float, bool)) else v
                for k, v in doc.metadata.items()
            }
            meta["topic"] = topic or DEFAULT_TOPIC
            metadatas.append(meta)

        collection.add(
            ids=ids,
            documents=contents,
            metadatas=metadatas,
        )

        return len(ids)

    def search(self, query, topic=None, top_k=3):
        """
        相似度检索

        Args:
            query: 查询文本
            topic: 主题名称。指定则只在该主题中检索，为 None 则检索所有主题
            top_k: 返回的最相关结果数量

        Returns:
            list[dict]: 检索结果列表，每项包含 content、metadata、distance
        """
        if topic:
            # 检索指定主题
            return self._search_collection(self._get_collection(topic), query, top_k)
        else:
            # 检索所有主题，合并结果后按距离排序取 top_k
            all_results = []
            for t in self.list_topics():
                collection = self._get_collection(t)
                all_results.extend(self._search_collection(collection, query, top_k))

            # 按距离升序排序（越小越相似），取 top_k
            all_results.sort(key=lambda x: x["distance"] if x["distance"] is not None else float("inf"))
            return all_results[:top_k]

    def _search_collection(self, collection, query, top_k):
        """
        在单个集合中执行相似度检索

        Args:
            collection: ChromaDB 集合对象
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            list[dict]: 检索结果列表
        """
        if collection.count() == 0:
            return []

        actual_k = min(top_k, collection.count())

        results = collection.query(
            query_texts=[query],
            n_results=actual_k,
        )

        search_results = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                search_results.append({
                    "chunk_id": meta.get("chunk_id", results["ids"][0][i] if results.get("ids") else ""),
                    "content": doc,
                    "metadata": meta,
                    "distance": results["distances"][0][i] if results["distances"] else None,
                })

        return search_results

    def list_topics(self):
        """
        列出所有主题

        Returns:
            list[str]: 主题名称列表
        """
        collections = self._client.list_collections()
        topics = []
        for col in collections:
            name = col.name if hasattr(col, "name") else str(col)
            if name.startswith(_COLLECTION_PREFIX):
                topics.append(name[len(_COLLECTION_PREFIX):])
        return sorted(topics)

    def get_stats(self, topic=None):
        """
        获取知识库统计信息

        Args:
            topic: 主题名称。指定则返回该主题统计，为 None 则返回全局统计

        Returns:
            dict: 统计信息字典
        """
        if topic:
            return self._get_collection_stats(topic)

        # 全局统计
        topics = self.list_topics()
        total_chunks = 0
        all_sources = set()
        topic_details = {}

        for t in topics:
            stats = self._get_collection_stats(t)
            total_chunks += stats["total_chunks"]
            all_sources.update(stats["sources"])
            topic_details[t] = stats

        return {
            "total_chunks": total_chunks,
            "sources": sorted(all_sources),
            "source_count": len(all_sources),
            "topic_count": len(topics),
            "topics": topic_details,
        }

    def _get_collection_stats(self, topic):
        """获取单个主题的统计信息"""
        collection = self._get_collection(topic)
        total = collection.count()

        sources = set()
        if total > 0:
            all_data = collection.get(include=["metadatas"])
            for meta in all_data["metadatas"]:
                source = meta.get("source", "未知")
                sources.add(source)

        return {
            "total_chunks": total,
            "sources": sorted(sources),
            "source_count": len(sources),
        }

    def clear(self, topic=None):
        """
        清空知识库

        Args:
            topic: 主题名称。指定则只清空该主题，为 None 则清空所有主题
        """
        if topic:
            collection_name = f"{_COLLECTION_PREFIX}{topic}"
            self._client.delete_collection(collection_name)
        else:
            for t in self.list_topics():
                collection_name = f"{_COLLECTION_PREFIX}{t}"
                self._client.delete_collection(collection_name)

    def delete_topic(self, topic):
        """
        删除指定主题及其所有数据

        Args:
            topic: 主题名称

        Raises:
            ValueError: 主题不存在
        """
        if topic not in self.list_topics():
            raise ValueError(f"主题不存在: {topic}")
        collection_name = f"{_COLLECTION_PREFIX}{topic}"
        self._client.delete_collection(collection_name)
