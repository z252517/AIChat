# -*- coding: utf-8 -*-

"""
网页搜索工具
基于 DuckDuckGo 搜索引擎（ddgs），无需 API Key
"""

from ai_chat_cli.tools.tool_base import ToolBase


class WebSearch(ToolBase):
    """网页搜索工具，使用 DuckDuckGo 搜索"""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "搜索互联网获取实时信息。输入搜索关键词，返回搜索结果摘要。适用于需要最新信息、事实查询等场景。"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数，默认 5",
                },
            },
            "required": ["query"],
        }

    def execute(self, **kwargs):
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 5)

        try:
            from ddgs import DDGS
        except ImportError:
            return "错误: 请先安装 ddgs 库 (pip install ddgs)"

        try:
            results = DDGS().text(query, max_results=max_results)

            if not results:
                return f"未找到关于 '{query}' 的搜索结果"

            output = []
            for i, r in enumerate(results, 1):
                title = r.get("title", "无标题")
                body = r.get("body", "无摘要")
                href = r.get("href", "")
                output.append(f"{i}. {title}\n   {body}\n   链接: {href}")

            return "\n\n".join(output)

        except Exception as e:
            return f"搜索失败: {str(e)}"
