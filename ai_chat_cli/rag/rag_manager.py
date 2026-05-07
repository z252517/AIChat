# -*- coding: utf-8 -*-

"""
RAG 管理器
统一管理知识库的文档入库、语义检索、主题管理等操作
所有 RAG 相关的业务逻辑集中在此，Tool 和 CLI 命令只需调用本类方法
"""

from ai_chat_cli.rag.document_loader import DocumentLoader
from ai_chat_cli.rag.text_splitter import TextSplitter
from ai_chat_cli.rag.vector_store import VectorStore
from ai_chat_cli.core.base.settings import Settings


class RAGManager:
    """
    RAG 管理器（单例 + 门面模式）

    封装 DocumentLoader、TextSplitter、VectorStore 的协作流程，
    对外提供简洁的高层 API，供 Tool 和 CLI 命令统一调用。

    支持两种检索模式:
        - 稠密检索: 仅使用 ChromaDB（默认 embedding）
        - 混合检索: 稠密 + BM25 稀疏，通过 RRF 融合（需安装 rank-bm25）
    """

    _instance = None

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        from ai_chat_cli.core.base.services import Service, ServiceKey
        self._logger = Service.get(ServiceKey.LOGGER)
        _settings = Settings.get_instance()
        self._store = VectorStore(_settings.RAG_DB_DIR)
        self._splitter = TextSplitter(
            chunk_size=_settings.RAG_CHUNK_SIZE,
            chunk_overlap=_settings.RAG_CHUNK_OVERLAP,
        )

        # 尝试启用混合检索（BM25 + RRF）
        self._sparse_store = None
        self._hybrid_searcher = None
        try:
            from ai_chat_cli.rag.sparse_store import SparseStore
            from ai_chat_cli.rag.hybrid_searcher import HybridSearcher

            self._sparse_store = SparseStore(_settings.RAG_DB_DIR)
            self._hybrid_searcher = HybridSearcher(self._store, self._sparse_store)
        except ImportError:
            # rank-bm25 未安装，降级为纯稠密检索
            pass

    @property
    def hybrid_enabled(self):
        """是否已启用混合检索"""
        return self._hybrid_searcher is not None

    @classmethod
    def get_instance(cls):
        """获取全局单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ==================== 文档入库 ====================

    def add_file(self, file_path, topic=None):
        """
        将文件加载、切分并存入知识库

        Args:
            file_path: 文件绝对路径（支持 .txt / .md / .pdf）
            topic: 主题名称，默认归入 'default'

        Returns:
            dict: {
                "success": bool,
                "message": str,
                "chunks_added": int,  # 成功入库的 chunk 数
            }
        """
        try:
            # 1. 加载文档
            documents = DocumentLoader.load(file_path)
            if not documents:
                return self._result(False, f"文件为空或无法解析: {file_path}")

            # 2. 切分文本
            chunks = self._splitter.split_documents(documents)
            if not chunks:
                return self._result(False, f"文件切分后无有效内容: {file_path}")

            # 3. 存入向量库（稠密）
            added_count = self._store.add_documents(chunks, topic=topic)

            # 4. 同步存入 BM25 稀疏索引
            if self._sparse_store is not None:
                try:
                    self._sparse_store.add_documents(chunks, topic=topic)
                except Exception as e:
                    self._logger.warning(f"BM25 索引写入失败（稠密存储已成功）: {e}")

            topic_info = f"，主题: {topic}" if topic else ""
            mode_info = "（混合检索）" if self.hybrid_enabled else "（稠密检索）"
            message = f"成功将 {file_path} 添加到知识库{topic_info}，共 {added_count} 个文档片段 {mode_info}"
            return self._result(True, message, chunks_added=added_count)

        except FileNotFoundError as e:
            return self._result(False, f"文件不存在: {e}")
        except ValueError as e:
            return self._result(False, f"文件格式错误: {e}")
        except ImportError as e:
            return self._result(False, str(e))
        except Exception as e:
            return self._result(False, f"知识入库失败: {e}")

    # ==================== 语义检索 ====================

    def search(self, query, topic=None, top_k=None):
        """
        从知识库中检索最相关的文档片段

        当 rank-bm25 可用时自动使用混合检索（稠密 + 稀疏 + RRF 融合），
        否则降级为纯稠密向量检索。

        Args:
            query: 查询文本
            topic: 限定检索的主题，为 None 则检索所有主题
            top_k: 返回结果数量，默认使用配置值

        Returns:
            dict: {
                "success": bool,
                "message": str,
                "results": list[dict],      # 原始检索结果
                "formatted": str,            # 格式化后的文本（供大模型消费）
                "mode": str,                 # "hybrid" 或 "dense"
            }
        """
        try:
            if not top_k:
                top_k = Settings.get_instance().RAG_TOP_K

            # 检查知识库是否为空
            stats = self._store.get_stats(topic)
            if stats["total_chunks"] == 0:
                topic_info = f"主题 '{topic}' 的" if topic else ""
                return self._result(False, f"{topic_info}知识库为空，请先添加文档")

            # 执行检索：优先混合检索，降级为纯稠密检索
            if self._hybrid_searcher is not None:
                results = self._hybrid_searcher.search(query, topic=topic, top_k=top_k)
                mode = "hybrid"
            else:
                results = self._store.search(query, topic=topic, top_k=top_k)
                mode = "dense"

            if not results:
                return self._result(False, f"未找到与 '{query}' 相关的内容")

            mode_label = "混合检索(稠密+BM25+RRF)" if mode == "hybrid" else "稠密检索"
            formatted = self._format_results(results, query, topic, mode)
            return self._result(
                True,
                f"[{mode_label}] 检索到 {len(results)} 个相关片段",
                results=results,
                formatted=formatted,
                mode=mode,
            )

        except ImportError as e:
            return self._result(False, str(e))
        except Exception as e:
            return self._result(False, f"知识检索失败: {e}")

    # ==================== 主题管理 ====================

    def list_topics(self):
        """
        列出所有主题

        Returns:
            list[str]: 主题名称列表
        """
        return self._store.list_topics()

    def get_stats(self, topic=None):
        """
        获取知识库统计信息

        Args:
            topic: 指定主题，为 None 则返回全局统计

        Returns:
            dict: 统计信息字典
        """
        return self._store.get_stats(topic)

    def clear(self, topic=None):
        """
        清空知识库

        Args:
            topic: 指定主题，为 None 则清空所有
        """
        self._store.clear(topic)
        if self._sparse_store is not None:
            self._sparse_store.clear(topic)

    def delete_topic(self, topic):
        """
        删除指定主题

        Args:
            topic: 主题名称

        Raises:
            ValueError: 主题不存在
        """
        self._store.delete_topic(topic)
        if self._sparse_store is not None:
            try:
                self._sparse_store.delete_topic(topic)
            except ValueError:
                pass  # BM25 侧可能没有该主题数据

    # ==================== 内部方法 ====================

    @staticmethod
    def _result(success, message, **extra):
        """构建统一的返回结果字典"""
        result = {"success": success, "message": message}
        result.update(extra)
        return result

    @staticmethod
    def _format_results(results, query, topic, mode="dense"):
        """
        将检索结果格式化为大模型易于理解的文本

        Args:
            results: 检索结果列表
            query: 原始查询
            topic: 检索主题
            mode: 检索模式 ("hybrid" 或 "dense")

        Returns:
            str: 格式化文本
        """
        topic_info = f"（主题: {topic}）" if topic else "（全部主题）"
        mode_label = "混合检索(稠密+BM25+RRF)" if mode == "hybrid" else "稠密向量检索"
        lines = [
            f"以下是从知识库{topic_info}中通过 [{mode_label}] 检索到的与 '{query}' 最相关的 {len(results)} 个片段：\n"
        ]

        for i, result in enumerate(results, 1):
            meta = result["metadata"]
            source = meta.get("source", "未知来源")
            page = meta.get("page", "")
            chunk_topic = meta.get("topic", "")

            # 构建来源信息
            source_parts = [f"来源: {source}"]
            if page:
                source_parts.append(f"第{page}页")
            if chunk_topic:
                source_parts.append(f"主题: {chunk_topic}")

            # 根据模式显示不同的分数信息
            if mode == "hybrid":
                rrf_score = result.get("rrf_score")
                dense_rank = result.get("dense_rank")
                sparse_rank = result.get("sparse_rank")
                if rrf_score is not None:
                    source_parts.append(f"RRF分数: {rrf_score:.6f}")
                if dense_rank is not None:
                    source_parts.append(f"稠密排名: #{dense_rank}")
                if sparse_rank is not None:
                    source_parts.append(f"BM25排名: #{sparse_rank}")
            else:
                distance = result.get("distance")
                if distance is not None:
                    source_parts.append(f"相似度距离: {distance:.4f}")

            source_info = " | ".join(source_parts)

            lines.append(f"--- 片段 {i} [{source_info}] ---")
            lines.append(result["content"])
            lines.append("")

        return "\n".join(lines)