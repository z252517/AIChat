# -*- coding: utf-8 -*-

"""
内置工具集合
所有随包分发的工具实现

注意：此处显式导入所有工具类，确保 PyInstaller 打包时能正确收集这些模块。
实际的工具加载仍由 ToolManager 根据 tools.yaml 配置动态完成。
"""

# -- PyInstaller hidden imports --
from ai_chat_cli.tools.builtin.web_search import WebSearch
from ai_chat_cli.tools.builtin.get_current_time import GetCurrentTime
from ai_chat_cli.tools.builtin.code_executor import CodeExecutor
from ai_chat_cli.tools.builtin.file_rw import FileRead, FileWrite
from ai_chat_cli.tools.builtin.knowledge_store import KnowledgeStore
from ai_chat_cli.tools.builtin.knowledge_search import KnowledgeSearch