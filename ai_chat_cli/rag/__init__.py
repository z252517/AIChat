# -*- coding: utf-8 -*-

"""
RAG (Retrieval-Augmented Generation) 模块
提供文档加载、文本分割、向量存储、混合检索等功能

模块结构:
    - document_loader : 文档加载（支持 .txt / .md / .pdf）
    - text_splitter   : 文本智能切分
    - vector_store    : 稠密向量检索（ChromaDB）
    - sparse_store    : 稀疏检索（BM25，需安装 rank-bm25）
    - hybrid_searcher : 混合检索 + RRF 融合
    - rag_manager     : 统一门面，对外提供高层 API
"""