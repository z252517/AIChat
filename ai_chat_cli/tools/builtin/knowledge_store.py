# -*- coding: utf-8 -*-

"""
知识入库工具
将本地文件加载、切分后添加到向量知识库中
"""

from ai_chat_cli.tools.tool_base import ToolBase
from ai_chat_cli.core.base.services import Service, ServiceKey


class KnowledgeStore(ToolBase):
    """知识入库工具，支持将 TXT/MD/PDF 文件添加到指定主题的知识库"""

    @property
    def name(self) -> str:
        return "knowledge_store"

    @property
    def description(self) -> str:
        return (
            "将本地文件添加到知识库中，支持 txt、md、pdf 格式。"
            "可指定主题分类（topic），不同主题的文档存储在独立集合中。"
            "添加后即可通过 knowledge_search 工具检索文件内容。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要添加到知识库的文件绝对路径（支持 .txt / .md / .pdf）",
                },
                "topic": {
                    "type": "string",
                    "description": "知识库主题分类名称（如 'finance'、'tech'），不指定则归入 'default' 主题",
                },
            },
            "required": ["file_path"],
        }

    def execute(self, **kwargs):
        logger = Service.get(ServiceKey.LOGGER)
        file_path = kwargs.get("file_path", "")
        topic = kwargs.get("topic", None)

        from ai_chat_cli.rag.rag_manager import RAGManager
        manager = RAGManager.get_instance()
        result = manager.add_file(file_path, topic=topic)

        if result["success"]:
            logger.info(result["message"])
        else:
            logger.error(result["message"])

        return result["message"]
