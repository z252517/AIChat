# -*- coding: utf-8 -*-

"""
文件读写工具
所有文件操作限制在 workspace 白名单目录内，防止路径遍历漏洞
"""

import os
from ai_chat_cli.tools.tool_base import ToolBase
from ai_chat_cli.core.base.settings import Settings


def _resolve_safe_path(file_path):
    """解析并校验路径必须在 workspace 内，返回规范化后的绝对路径"""
    settings = Settings.get_instance()
    workspace = os.path.realpath(settings.WORKSPACE_DIR)

    if not file_path:
        raise ValueError("文件路径不能为空")

    if not os.path.isabs(file_path):
        file_path = os.path.join(workspace, file_path)

    resolved = os.path.realpath(file_path)
    common = os.path.commonpath([resolved, workspace])

    if common != workspace:
        raise ValueError(
            f"安全限制: 文件路径必须在 workspace 目录内\n"
            f"  workspace: {workspace}\n"
            f"  请求路径: {resolved}"
        )

    return resolved


class FileRead(ToolBase):
    """读取本地文件内容（仅限 workspace 目录内）"""

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return (
            "读取本地文件内容。"
            "支持文本文件（txt, py, json, yaml, md 等）。"
            "注意：只能读取 workspace 目录内的文件。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径，可以是 workspace 内的相对路径或 workspace 下的绝对路径",
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码，默认 utf-8",
                },
            },
            "required": ["file_path"],
        }

    def execute(self, **kwargs):
        file_path = kwargs.get("file_path", "")
        encoding = kwargs.get("encoding", "utf-8")

        try:
            safe_path = _resolve_safe_path(file_path)
        except ValueError as e:
            return str(e)

        if not os.path.exists(safe_path):
            return f"错误: 文件不存在 - {safe_path}"

        if not os.path.isfile(safe_path):
            return f"错误: 路径不是文件 - {safe_path}"

        try:
            with open(safe_path, "r", encoding=encoding) as f:
                content = f.read()

            max_chars = 10000
            if len(content) > max_chars:
                content = content[:max_chars] + f"\n\n... (文件过大，已截断，共 {len(content)} 字符)"

            return content

        except Exception as e:
            return f"读取文件失败: {str(e)}"


class FileWrite(ToolBase):
    """写入内容到本地文件（仅限 workspace 目录内）"""

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return (
            "将内容写入本地文件。"
            "默认使用安全模式 'x'（仅在文件不存在时创建，防止意外覆盖）。"
            "如需覆盖已有文件请使用 mode='w'，如需追加请使用 mode='a'。"
            "注意：只能写入 workspace 目录内的文件。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件路径，可以是 workspace 内的相对路径或 workspace 下的绝对路径",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的文件内容",
                },
                "mode": {
                    "type": "string",
                    "description": "写入模式: 'x' 安全创建（默认，文件存在则失败），'w' 覆盖写入，'a' 追加写入",
                    "enum": ["x", "w", "a"],
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码，默认 utf-8",
                },
            },
            "required": ["file_path", "content"],
        }

    def execute(self, **kwargs):
        file_path = kwargs.get("file_path", "")
        content = kwargs.get("content", "")
        mode = kwargs.get("mode", "x")
        encoding = kwargs.get("encoding", "utf-8")

        try:
            safe_path = _resolve_safe_path(file_path)
        except ValueError as e:
            return str(e)

        try:
            dir_path = os.path.dirname(safe_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)

            with open(safe_path, mode, encoding=encoding) as f:
                f.write(content)

            if mode == "x":
                action = "安全创建"
            elif mode == "a":
                action = "追加写入"
            else:
                action = "覆盖写入"
            return f"成功{action}文件: {safe_path} ({len(content)} 字符)"

        except FileExistsError:
            return f"错误: 文件已存在 - {safe_path}（使用 mode='w' 覆盖或 mode='a' 追加）"
        except Exception as e:
            return f"写入文件失败: {str(e)}"
