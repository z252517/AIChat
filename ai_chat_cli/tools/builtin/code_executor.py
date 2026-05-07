# -*- coding: utf-8 -*-

"""
Python 代码执行工具
在子进程中隔离执行 Python 代码，限制危险操作
"""

import subprocess
import sys
from ai_chat_cli.tools.tool_base import ToolBase

_EXECUTION_TIMEOUT = 10  # 代码执行超时（秒）


class CodeExecutor(ToolBase):
    """在隔离子进程中安全执行 Python 代码"""

    @property
    def name(self) -> str:
        return "execute_python"

    @property
    def description(self) -> str:
        return (
            "执行一段 Python 代码并返回输出结果。"
            "适用于数学计算、数据处理、字符串操作等场景。"
            "代码中使用 print() 输出结果。"
            "注意：代码在独立子进程中执行，超时限制为10秒。"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码",
                },
            },
            "required": ["code"],
        }

    def execute(self, **kwargs):
        code = kwargs.get("code", "")

        if not code.strip():
            return "错误: 代码不能为空"

        try:
            result = subprocess.run(
                [sys.executable, "-I", "-c", code],
                capture_output=True,
                text=True,
                timeout=_EXECUTION_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return f"错误: 代码执行超时（{_EXECUTION_TIMEOUT}秒）"

        lines = []
        if result.stdout:
            lines.append(result.stdout.rstrip())
        if result.stderr:
            lines.append("[stderr]")
            lines.append(result.stderr.rstrip())

        output = "\n".join(lines)
        if not output:
            return "(代码执行成功，无输出)"
        return output
