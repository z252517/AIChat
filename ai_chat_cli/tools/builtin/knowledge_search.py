# -*- coding: utf-8 -*-

"""
知识检索工具
从向量知识库中检索与查询最相关的文档片段
"""

from ai_chat_cli.tools.tool_base import ToolBase
from ai_chat_cli.core.base.services import Service, ServiceKey


class KnowledgeSearch(ToolBase):
    """知识检索工具，从知识库中语义检索相关文档片段"""

    @property
    def name(self) -> str:
        return "knowledge_search"

    @property
    def description(self) -> str:
        return (
            "从知识库中检索与查询最相关的文档片段，用于回答用户基于已入库文档的问题。"
            "可指定主题（topic）仅在特定领域中检索，不指定则在所有主题中检索。"
            "知识库为空时无法检索，需先通过 knowledge_store 工具添加文档。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "检索关键词或问题描述，将基于语义相似度匹配最相关的文档片段",
                },
                "topic": {
                    "type": "string",
                    "description": "限定检索的主题分类名称（如 'finance'、'tech'），不指定则在所有主题中检索",
                },
                "top_k": {
                    "type": "integer",
                    "description": "返回的最相关结果数量，默认为 3",
                },
            },
            "required": ["query"],
        }

    def execute(self, **kwargs):
        logger = Service.get(ServiceKey.LOGGER)
        query = kwargs.get("query", "")
        topic = kwargs.get("topic", None)
        top_k = kwargs.get("top_k", None)

        from ai_chat_cli.rag.rag_manager import RAGManager
        manager = RAGManager.get_instance()
        result = manager.search(query, topic=topic, top_k=top_k)

        if result["success"]:
            logger.debug(f"知识检索: query='{query[:50]}', topic={topic}, {result['message']}")
            return result["formatted"]
        else:
            return result["message"]
