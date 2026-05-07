# -*- coding: utf-8 -*-

"""
稀疏检索存储
基于 BM25 算法的稀疏向量检索，与 ChromaDB 的稠密检索互补，用于混合检索
"""

import json
import logging
import os
import re

import numpy as np

from ai_chat_cli.rag.document_loader import Document

_logger = logging.getLogger(__name__)


# 与 vector_store 保持一致的默认主题
DEFAULT_TOPIC = "default"


def _tokenize(text):
    """
    对文本进行分词

    优先使用 jieba 分词（中文友好），不可用时降级为正则切分。
    """
    try:
        import jieba
        # jieba 对中英文混合文本都能很好地处理
        tokens = jieba.lcut_for_search(text)
    except ImportError:
        # 降级方案：按非字母数字的中文字符边界切分
        # 英文按空格/标点切分，中文逐字切分
        tokens = re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]", text.lower())

    # 过滤空白和过短 token
    return [t.strip().lower() for t in tokens if t.strip() and len(t.strip()) > 1]


class SparseStore:
    """
    BM25 稀疏检索存储

    每个主题维护一个独立的 BM25 索引，文档语料持久化到 JSON 文件，
    启动时自动加载并重建索引。
    """

    def __init__(self, persist_dir):
        """
        Args:
            persist_dir: 持久化目录（与 VectorStore 共用父目录即可）
        """
        try:
            from rank_bm25 import BM25Okapi  # noqa: F401
        except ImportError:
            raise ImportError(
                "混合检索需要 rank_bm25 库，请运行: pip install rank-bm25"
            )

        self._persist_dir = os.path.join(persist_dir, "_bm25")
        os.makedirs(self._persist_dir, exist_ok=True)

        # topic -> { "corpus": [...], "index": BM25Okapi | None }
        self._topics: dict = {}
        self._dirty: dict = {}  # topic -> bool，标记是否需要重建索引

        # 加载已有数据
        self._load_all()

    # ==================== 公开 API ====================

    def add_documents(self, documents, topic=None):
        """
        将 Document 列表添加到 BM25 语料库并重建索引

        Args:
            documents: Document 列表
            topic: 主题名称

        Returns:
            int: 成功添加的文档数量
        """
        if not documents:
            return 0

        topic = topic or DEFAULT_TOPIC
        self._ensure_topic(topic)

        for doc in documents:
            self._topics[topic]["corpus"].append({
                "content": doc.content,
                "metadata": doc.metadata,
                "chunk_id": doc.metadata.get("chunk_id", ""),
            })

        self._dirty[topic] = True
        self._save_topic(topic)
        return len(documents)

    def search(self, query, topic=None, top_k=3):
        """
        BM25 稀疏检索

        Args:
            query: 查询文本
            topic: 主题名称，为 None 则检索所有主题
            top_k: 返回结果数量

        Returns:
            list[dict]: 检索结果，每项包含 content、metadata、score
        """
        if topic:
            return self._search_topic(topic, query, top_k)
        else:
            # 检索所有主题，合并后按分数降序取 top_k
            all_results = []
            for t in self.list_topics():
                all_results.extend(self._search_topic(t, query, top_k))
            all_results.sort(key=lambda x: x["score"], reverse=True)
            return all_results[:top_k]

    def list_topics(self):
        """列出所有有数据的主题"""
        return sorted(
            t for t, data in self._topics.items() if data["corpus"]
        )

    def clear(self, topic=None):
        """清空语料库"""
        if topic:
            self._topics.pop(topic, None)
            self._delete_topic_file(topic)
        else:
            for t in list(self._topics.keys()):
                self._delete_topic_file(t)
            self._topics.clear()

    def delete_topic(self, topic):
        """删除指定主题"""
        if topic not in self._topics:
            raise ValueError(f"BM25 主题不存在: {topic}")
        self._topics.pop(topic)
        self._delete_topic_file(topic)

    # ==================== 内部方法 ====================

    def _ensure_topic(self, topic):
        if topic not in self._topics:
            self._topics[topic] = {"corpus": [], "index": None}

    def _rebuild_index(self, topic):
        """根据当前语料重建 BM25 索引"""
        from rank_bm25 import BM25Okapi

        corpus = self._topics[topic]["corpus"]
        if not corpus:
            self._topics[topic]["index"] = None
            return

        tokenized_corpus = [_tokenize(doc["content"]) for doc in corpus]
        self._topics[topic]["index"] = BM25Okapi(tokenized_corpus)

    def _search_topic(self, topic, query, top_k):
        """在单个主题中执行 BM25 检索"""
        self._ensure_topic(topic)
        data = self._topics[topic]

        # 懒重建：如果有新文档加入，搜索前才重建索引
        if self._dirty.get(topic, False):
            self._rebuild_index(topic)
            self._dirty[topic] = False

        if not data["corpus"] or data["index"] is None:
            return []

        tokenized_query = _tokenize(query)
        if not tokenized_query:
            return []

        scores = data["index"].get_scores(tokenized_query)
        actual_k = min(top_k, len(data["corpus"]))

        # 取 top_k 个最高分
        top_indices = np.argsort(scores)[::-1][:actual_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score <= 0:
                continue  # 跳过零分结果
            doc = data["corpus"][idx]
            results.append({
                "chunk_id": doc.get("chunk_id") or "",
                "content": doc["content"],
                "metadata": doc["metadata"],
                "score": score,
            })

        return results

    # ---------- 持久化 ----------

    def _topic_file(self, topic):
        return os.path.join(self._persist_dir, f"{topic}.json")

    def _save_topic(self, topic):
        """将主题语料保存到磁盘"""
        data = self._topics.get(topic)
        if not data:
            return
        with open(self._topic_file(topic), "w", encoding="utf-8") as f:
            json.dump(data["corpus"], f, ensure_ascii=False, indent=2)

    def _load_all(self):
        """启动时加载所有已持久化的主题"""
        if not os.path.isdir(self._persist_dir):
            return
        for filename in os.listdir(self._persist_dir):
            if not filename.endswith(".json"):
                continue
            topic = filename[:-5]  # 去掉 .json
            filepath = os.path.join(self._persist_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    corpus = json.load(f)
                self._topics[topic] = {"corpus": corpus, "index": None}
                self._rebuild_index(topic)
            except (json.JSONDecodeError, KeyError) as e:
                _logger.warning(f"跳过损坏的 BM25 索引文件 {filename}: {e}")

    def _delete_topic_file(self, topic):
        filepath = self._topic_file(topic)
        if os.path.exists(filepath):
            os.remove(filepath)
