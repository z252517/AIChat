# -*- coding: utf-8 -*-

"""
文档加载器
支持加载 TXT、Markdown、PDF 格式的文件，返回统一的文档结构
"""

import os


class Document:
    """统一的文档结构"""

    def __init__(self, content, metadata=None):
        """
        Args:
            content: 文档文本内容
            metadata: 元数据字典（来源文件、页码等）
        """
        self.content = content
        self.metadata = metadata or {}

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"Document(content='{preview}', metadata={self.metadata})"


class DocumentLoader:
    """文档加载器，根据文件扩展名选择对应的解析策略"""

    SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_PDF_PAGES = 500

    @classmethod
    def load(cls, file_path):
        """
        加载文件并返回 Document 列表

        Args:
            file_path: 文件绝对路径

        Returns:
            list[Document]: 文档列表（PDF 可能多页，每页一个 Document）

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的文件格式
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"不支持的文件格式: {ext}，支持: {cls.SUPPORTED_EXTENSIONS}")

        file_name = os.path.basename(file_path)

        if ext == ".pdf":
            return cls._load_pdf(file_path, file_name)
        else:
            return cls._load_text(file_path, file_name)

    @classmethod
    def _read_file_with_fallback(cls, file_path):
        """读取文件，自动检测编码（一次 I/O + 内存解码）"""
        with open(file_path, "rb") as f:
            raw = f.read()
        for encoding in ['utf-8', 'gbk', 'gb18030', 'latin-1']:
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue

    @classmethod
    def _load_text(cls, file_path, file_name):
        """加载文本文件（TXT / Markdown）"""
        file_size = os.path.getsize(file_path)
        if file_size > cls.MAX_FILE_SIZE:
            raise ValueError(f"文件过大: {file_size / 1024 / 1024:.1f}MB，最大支持 {cls.MAX_FILE_SIZE / 1024 / 1024:.0f}MB")

        content = cls._read_file_with_fallback(file_path)

        if not content.strip():
            return []

        return [Document(
            content=content,
            metadata={"source": file_name, "file_path": file_path}
        )]

    @classmethod
    def _load_pdf(cls, file_path, file_name):
        """加载 PDF 文件（每页一个 Document）"""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError(
                "加载 PDF 需要 PyMuPDF 库，请运行: pip install PyMuPDF"
            )

        documents = []
        with fitz.open(file_path) as pdf:
            total_pages = len(pdf)
            max_pages = min(total_pages, cls.MAX_PDF_PAGES)

            for page_num in range(max_pages):
                page = pdf[page_num]
                text = page.get_text()
                if text.strip():
                    documents.append(Document(
                        content=text,
                        metadata={
                            "source": file_name,
                            "file_path": file_path,
                            "page": page_num + 1,
                            "total_pages": total_pages,
                        }
                    ))

        return documents
