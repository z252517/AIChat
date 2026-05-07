# -*- coding: utf-8 -*-

"""
工具执行器
负责执行模型发起的工具调用并将结果追加到消息历史
"""

import json

from ai_chat_cli.core.base.services import Service, ServiceKey


class ToolExecutor:
    """工具调用执行器"""

    def __init__(self, tools_map, messages):
        """
        Args:
            tools_map: ChatConfig.tools_map 的引用
            messages: ChatHistory.messages 的引用
        """
        self._tools_map = tools_map
        self._messages = messages
        self._logger = Service.get(ServiceKey.LOGGER)

    # ==================== 公共方法 ====================

    def execute(self, result):
        """
        执行工具调用并将结果追加到消息历史

        Args:
            result: _StreamResult，包含 tool_calls_map
        """
        display = Service.get(ServiceKey.DISPLAY)

        # 构造 tool_calls 列表并逐个执行（单次遍历）
        tool_calls = []
        for idx in sorted(result.tool_calls_map.keys()):
            tc = result.tool_calls_map[idx]
            tool_calls.append({
                "id": tc["id"],
                "type": "function",
                "function": {"name": tc["name"], "arguments": tc["arguments"]},
            })

        # 追加 assistant 消息（包含所有 tool_calls）
        assistant_msg = {"role": "assistant", "content": "", "tool_calls": tool_calls}
        if result.reasoning_content:
            assistant_msg["reasoning_content"] = result.reasoning_content
        self._messages.append(assistant_msg)

        # 逐个执行工具并追加结果
        for idx in sorted(result.tool_calls_map.keys()):
            tc = result.tool_calls_map[idx]
            name, args_str, call_id = tc["name"], tc["arguments"], tc["id"]
            args = json.loads(args_str) if args_str else {}

            if name not in self._tools_map:
                raise ValueError(f"未找到工具: {name}")

            self._logger.debug(f"执行工具: {name}, 参数: {args}")

            display.tool_executing(name)
            try:
                tool_result = self._tools_map[name].execute(**args)
            except Exception as e:
                self._logger.error(f"工具 {name} 执行异常: {e}")
                tool_result = f"工具执行失败: {e}"
            result_str = json.dumps(tool_result, default=str, ensure_ascii=False) if not isinstance(tool_result, str) else tool_result
            display.tool_result(result_str)
            self._logger.debug(f"工具返回: {result_str[:200]}")

            self._messages.append({"role": "tool", "tool_call_id": call_id, "content": result_str})

        display.tool_call_end()
