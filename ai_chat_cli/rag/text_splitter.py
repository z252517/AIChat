# -*- coding: utf-8 -*-

"""
文本分割器
将长文档按 chunk 切分，支持智能分割（优先按段落/换行符切分）
"""

import uuid

from ai_chat_cli.rag.document_loader import Document


class TextSplitter:
    """文本分割器，将 Document 切分为更小的 chunk"""

    # 分割符优先级（从高到低）
    SEPARATORS = ["\n\n", "\n", "。", ".", "！", "!", "？", "?", "；", ";", " "]

    def __init__(self, chunk_size=500, chunk_overlap=50):
        """
        Args:
            chunk_size: 每个 chunk 的最大字符数
            chunk_overlap: 相邻 chunk 之间的重叠字符数
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_documents(self, documents):
        """
        将 Document 列表切分为更小的 chunk Document 列表

        Args:
            documents: Document 列表

        Returns:
            list[Document]: 切分后的 Document 列表，每个 chunk 继承原文档的 metadata
        """
        chunks = []
        for doc in documents:
            text_chunks = self._split_text(doc.content)
            for i, chunk_text in enumerate(text_chunks):
                chunk_metadata = dict(doc.metadata)
                chunk_metadata["chunk_index"] = i
                chunk_metadata["total_chunks"] = len(text_chunks)
                chunk_metadata["chunk_id"] = uuid.uuid4().hex
                chunks.append(Document(content=chunk_text, metadata=chunk_metadata))
        return chunks

    def _split_text(self, text):
        """
        将文本按 chunk_size 切分，智能选择分割点

        Args:
            text: 待切分的文本

        Returns:
            list[str]: 切分后的文本片段列表
        """
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        chunks = []
        start = 0

        while start < len(text):
            # 取一个窗口
            end = start + self.chunk_size

            if end >= len(text):
                # 剩余文本不足一个 chunk，直接取完
                chunk = text[start:]
                if chunk.strip():
                    chunks.append(chunk.strip())
                break

            # 在窗口内寻找最佳分割点
            chunk = text[start:end]
            split_pos = self._find_split_position(chunk)

            if split_pos > 0:
                chunk = text[start:start + split_pos]
            # 否则直接在 chunk_size 处硬切

            if chunk.strip():
                chunks.append(chunk.strip())

            # 计算下一个起始位置（考虑 overlap）
            actual_end = start + len(chunk)
            start = max(actual_end - self.chunk_overlap, start + 1)

        return chunks

    def _find_split_position(self, text):
        """
        在文本中找到最佳分割位置（从后往前找分割符，使 chunk 尽可能大）

        Args:
            text: 窗口内的文本

        Returns:
            int: 分割位置（0 表示未找到合适位置）
        """
        # 只在后半部分查找分割点，避免 chunk 太小
        search_start = len(text) // 2

        for sep in self.SEPARATORS:
            pos = text.rfind(sep, search_start)
            if pos > 0:
                return pos + len(sep)

        return 0
