# -*- coding: utf-8 -*-

"""
请求发送器
封装 OpenAI API 的流式请求发送和重试机制
"""

import time

from openai import OpenAI

from ai_chat_cli.core.base.services import Service, ServiceKey
from ai_chat_cli.core.base.settings import Settings
from ai_chat_cli.core.chat.streaming import StreamHandler


class RequestSender:
    """API 请求发送器"""

    def __init__(self, api_key, base_url, token_tracker):
        self._client = OpenAI(api_key=api_key, base_url=base_url)
        self._model = Settings.get_instance().MODEL.model_name if Settings.get_instance().MODEL else ""
        self._stream_handler = StreamHandler()
        self._token_tracker = token_tracker
        self._logger = Service.get(ServiceKey.LOGGER)

    # ==================== 公共方法 ====================

    def set_model_name(self, model_name):
        """更新模型名称"""
        self._model = model_name

    def rebuild_client(self, api_key, base_url):
        """根据新配置重建 OpenAI 客户端"""
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def send(self, messages, tools, **kwargs):
        """
        发送请求并处理流式响应，内置重试机制

        Args:
            messages: 消息列表
            tools: 工具定义列表

        Returns:
            _StreamResult: 流式处理结果
        """
        settings = Settings.get_instance()
        last_error = None

        for attempt in range(1, settings.MAX_RETRIES + 1):
            try:
                result = self._stream_handler.process(
                    lambda: self._send_request(messages, tools, **kwargs)
                )
                self._token_tracker.track(result.usage)
                return result
            except Exception as e:
                last_error = e
                self._logger.warning(f"请求失败 (第 {attempt}/{settings.MAX_RETRIES} 次): {e}")
                if attempt < settings.MAX_RETRIES:
                    self._logger.info(f"等待 {settings.RETRY_DELAY}s 后重试...")
                    time.sleep(settings.RETRY_DELAY)

        self._logger.error(f"重试 {settings.MAX_RETRIES} 次后仍然失败")
        raise last_error

    # ==================== 内部方法 ====================

    def _send_request(self, messages, tools, **kwargs):
        """构建参数并发送流式请求"""
        params = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if tools:
            params["tools"] = tools
        params.update(kwargs)
        return self._client.chat.completions.create(**params)
