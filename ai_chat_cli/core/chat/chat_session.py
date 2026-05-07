# -*- coding: utf-8 -*-

"""
对话会话
实现 ReAct 循环：用户消息 → 模型响应 → 工具调用 → 再次响应，含三层防护
"""

from ai_chat_cli.core.base.services import Service, ServiceKey
from ai_chat_cli.core.base.settings import Settings


class ChatSession:
    """对话会话，管理 ReAct 循环"""

    def __init__(self, messages, tools, request_sender, tool_executor):
        """
        Args:
            messages: ChatHistory.messages 的引用
            tools: ChatConfig.tools 的引用（Python 列表引用传递，随注册更新自动同步）
            request_sender: RequestSender 实例
            tool_executor: ToolExecutor 实例
        """
        self._messages = messages
        self._tools = tools
        self._request_sender = request_sender
        self._tool_executor = tool_executor
        self._logger = Service.get(ServiceKey.LOGGER)

    # ==================== 公共方法 ====================

    def chat(self, user_message, **kwargs):
        """
        发送用户消息并获取最终回复
        自动处理工具调用循环，含三层防护：重复检测 -> Token 预算 -> 兜底上限

        Args:
            user_message: 用户消息内容
            **kwargs: 额外参数传递给 API

        Returns:
            str: 模型的最终回复文本
        """
        self._messages.append({"role": "user", "content": user_message})
        self._logger.debug(f"用户消息: {user_message[:100]}")

        settings = Settings.get_instance()
        result = self._request_sender.send(self._messages, self._tools, **kwargs)
        tool_round = 0
        session_tokens = result.usage.get("total_tokens", 0) if result.usage else 0
        last_signature = None
        stale_count = 0

        while result.finish_reason == "tool_calls" and result.tool_calls_map:
            tool_round += 1

            # --- 防护层 1: 重复检测（最早触发、最常见）---
            this_signature = self._make_tool_calls_signature(result.tool_calls_map)
            if this_signature == last_signature:
                stale_count += 1
            else:
                stale_count = 1
            last_signature = this_signature

            if stale_count >= settings.TOOL_STALE_ROUNDS:
                self._logger.warning(
                    f"检测到重复工具调用（连续 {stale_count} 轮），终止循环"
                )
                warning = (
                    f"检测到连续 {stale_count} 轮调用相同工具和参数，"
                    f"任务可能陷入死循环，已自动终止"
                )
                self._messages.append({"role": "assistant", "content": warning})
                return warning

            # --- 防护层 2: Token 预算 ---
            if session_tokens > settings.TOOL_MAX_TOKENS:
                self._logger.warning(
                    f"工具调用 Token 已超预算（{session_tokens}/{settings.TOOL_MAX_TOKENS}）"
                )
                warning = (
                    f"工具调用已消耗 {session_tokens} tokens，"
                    f"超过预算上限 {settings.TOOL_MAX_TOKENS}，"
                    f"任务可能过于复杂，请拆分或调整 tool.max_tool_tokens 配置"
                )
                self._messages.append({"role": "assistant", "content": warning})
                return warning

            # --- 防护层 3: 兜底上限（最终安全网）---
            if tool_round > settings.MAX_TOOL_ROUNDS:
                self._logger.warning(
                    f"工具调用已达上限 {settings.MAX_TOOL_ROUNDS} 轮，终止循环"
                )
                warning = (
                    f"工具调用已达到最大轮次限制（{settings.MAX_TOOL_ROUNDS}轮），"
                    f"请简化任务或调整 tool.max_rounds 配置"
                )
                self._messages.append({"role": "assistant", "content": warning})
                return warning

            # --- 正常路径: 执行工具 ---
            self._tool_executor.execute(result)
            result = self._request_sender.send(self._messages, self._tools, **kwargs)
            if result.usage:
                session_tokens += result.usage.get("total_tokens", 0)

        if result.content:
            self._messages.append({"role": "assistant", "content": result.content})
        return result.content

    # ==================== 内部方法 ====================

    @staticmethod
    def _make_tool_calls_signature(tool_calls_map):
        """将本轮工具调用列表转换为可比较的签名，用于检测连续重复"""
        calls = []
        for idx in sorted(tool_calls_map.keys()):
            tc = tool_calls_map[idx]
            calls.append((tc["name"], tc.get("arguments", "")))
        return tuple(calls)
