# -*- coding: utf-8 -*-

"""
聊天配置管理
负责模型切换、API Key 更新、系统提示词和工具注册
"""

from ai_chat_cli.core.base.settings import Settings


class ChatConfig:
    """聊天配置管理器"""

    def __init__(self, messages, request_sender):
        """
        Args:
            messages: ChatHistory.messages 的引用（Python 列表引用传递）
            request_sender: RequestSender 实例，用于重建 API 客户端
        """
        self._messages = messages
        self._request_sender = request_sender
        self.tools = []             # OpenAI function calling 格式的工具定义
        self.tools_map = {}         # {tool_name: ToolBase 实例}

    # ==================== 公共方法 ====================

    def set_model(self, model):
        """设置使用的模型（同时重建 API 客户端）"""
        from ai_chat_cli.core.base.models import ModelType, Model
        if not isinstance(model, ModelType):
            raise ValueError(f"无效的模型，可选: {Model.list_names()}")
        settings = Settings.get_instance()
        settings.BASE_URL = model.base_url
        self._request_sender.rebuild_client(settings.API_KEY, model.base_url)
        self._request_sender.set_model_name(model.model_name)

    def set_api_key(self, api_key):
        """设置 API Key（同时重建 API 客户端）"""
        settings = Settings.get_instance()
        settings.API_KEY = api_key
        self._request_sender.rebuild_client(api_key, settings.BASE_URL)

    def set_system_prompt(self, prompt):
        """设置系统提示词（已有则替换，否则插入最前面）"""
        system_msg = {"role": "system", "content": prompt}
        if self._messages and self._messages[0]["role"] == "system":
            self._messages[0] = system_msg
        else:
            self._messages.insert(0, system_msg)

    def register_tools(self, tool_map):
        """注册工具映射表"""
        self.tools_map = tool_map
        self.tools = [tool.to_tool_dict() for tool in tool_map.values()]
