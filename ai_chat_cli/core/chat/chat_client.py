# -*- coding: utf-8 -*-

"""
聊天客户端
门面模式：组合各子模块，对外暴露统一接口
"""

from ai_chat_cli.core.chat.token_tracker import TokenTracker
from ai_chat_cli.core.chat.chat_history import ChatHistory
from ai_chat_cli.core.chat.chat_config import ChatConfig
from ai_chat_cli.core.chat.request_sender import RequestSender
from ai_chat_cli.core.chat.tool_executor import ToolExecutor
from ai_chat_cli.core.chat.chat_session import ChatSession


class ChatClient:
    """聊天客户端门面，组合各子模块"""

    def __init__(self, api_key, base_url):
        self._token_tracker = TokenTracker()
        self._history = ChatHistory()
        self._request_sender = RequestSender(api_key, base_url, self._token_tracker)
        self._config = ChatConfig(self._history.messages, self._request_sender)
        self._tool_executor = ToolExecutor(self._config.tools_map, self._history.messages)
        self._session = ChatSession(
            self._history.messages, self._config.tools,
            self._request_sender, self._tool_executor,
        )

    # ==================== 属性 ====================

    @property
    def messages(self):
        return self._history.messages

    # ==================== 配置（委托 ChatConfig）====================

    def set_model(self, model):
        self._config.set_model(model)

    def set_api_key(self, api_key):
        self._config.set_api_key(api_key)

    def set_system_prompt(self, prompt):
        self._config.set_system_prompt(prompt)

    def register_tools(self, tool_map):
        self._config.register_tools(tool_map)

    # ==================== 对话（委托 ChatSession）====================

    def chat(self, user_message, **kwargs):
        return self._session.chat(user_message, **kwargs)

    # ==================== 历史（委托 ChatHistory）====================

    def clear_history(self):
        self._history.clear()

    def save_history(self, filename=None):
        return self._history.save(filename)

    def load_history(self, filepath):
        return self._history.load(filepath)

    # ==================== Token（委托 TokenTracker）====================

    def get_token_usage(self):
        return self._token_tracker.get_total()
