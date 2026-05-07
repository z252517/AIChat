# -*- coding: utf-8 -*-

"""
混合检索器
结合稠密向量检索（ChromaDB）和稀疏检索（BM25），
使用 Reciprocal Rank Fusion (RRF) 算法融合两路结果
"""


class HybridSearcher:
    """
    混合检索器

    工作流程:
        1. 稠密检索 (ChromaDB embedding) → 排序列表 A
        2. 稀疏检索 (BM25)               → 排序列表 B
        3. RRF 融合                       → 最终排序列表

    RRF 公式: score(d) = Σ 1 / (k + rank_i(d))
    其中 k 为常数（默认 60），rank_i(d) 为文档 d 在第 i 路检索中的排名（从 1 开始）
    """

    def __init__(self, vector_store, sparse_store):
        """
        Args:
            vector_store: VectorStore 实例（稠密检索）
            sparse_store: SparseStore 实例（稀疏检索）
        """
        self._dense = vector_store
        self._sparse = sparse_store

    def search(self, query, topic=None, top_k=3, rrf_k=60):
        """
        执行混合检索

        Args:
            query: 查询文本
            topic: 主题名称，为 None 则检索所有主题
            top_k: 最终返回的结果数量
            rrf_k: RRF 融合常数，值越大各路排名差异越平滑（默认 60）

        Returns:
            list[dict]: 融合后的检索结果，每项包含:
                - content: 文本内容
                - metadata: 元数据
                - rrf_score: RRF 融合分数
                - dense_rank: 稠密检索排名（None 表示未命中）
                - sparse_rank: 稀疏检索排名（None 表示未命中）
        """
        # 两路检索各取更多候选，确保融合后有足够结果
        fetch_k = top_k * 3

        # 1. 稠密检索（ChromaDB）
        dense_results = self._dense.search(query, topic=topic, top_k=fetch_k)

        # 2. 稀疏检索（BM25）
        sparse_results = self._sparse.search(query, topic=topic, top_k=fetch_k)

        # 3. RRF 融合
        fused = self._rrf_fusion(dense_results, sparse_results, rrf_k=rrf_k)

        # 4. 取 top_k 并返回
        return fused[:top_k]

    @staticmethod
    def _rrf_fusion(dense_results, sparse_results, rrf_k=60):
        """
        Reciprocal Rank Fusion 融合算法

        Args:
            dense_results: 稠密检索结果（按距离升序，distance 越小越好）
            sparse_results: 稀疏检索结果（按 BM25 score 降序，score 越大越好）
            rrf_k: 融合常数

        Returns:
            list[dict]: 按 RRF 分数降序排列的融合结果
        """
        # 用 chunk_id 作为文档唯一标识来匹配两路结果
        doc_map = {}  # chunk_id -> { 文档信息 + 排名 }

        # 处理稠密检索结果（已按距离升序排列，rank 从 1 开始）
        for rank, item in enumerate(dense_results, start=1):
            key = item.get("chunk_id") or item["content"]
            if key not in doc_map:
                doc_map[key] = {
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "chunk_id": key,
                    "dense_rank": None,
                    "sparse_rank": None,
                    "rrf_score": 0.0,
                }
            doc_map[key]["dense_rank"] = rank

        # 处理稀疏检索结果（已按分数降序排列，rank 从 1 开始）
        for rank, item in enumerate(sparse_results, start=1):
            key = item.get("chunk_id") or item["content"]
            if key not in doc_map:
                doc_map[key] = {
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "chunk_id": key,
                    "dense_rank": None,
                    "sparse_rank": None,
                    "rrf_score": 0.0,
                }
            doc_map[key]["sparse_rank"] = rank

        # 计算 RRF 分数
        for doc in doc_map.values():
            if doc["dense_rank"] is not None:
                doc["rrf_score"] += 1.0 / (rrf_k + doc["dense_rank"])
            if doc["sparse_rank"] is not None:
                doc["rrf_score"] += 1.0 / (rrf_k + doc["sparse_rank"])

        # 按 RRF 分数降序排列
        fused = sorted(doc_map.values(), key=lambda x: x["rrf_score"], reverse=True)
        return fused
