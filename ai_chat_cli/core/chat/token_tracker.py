# -*- coding: utf-8 -*-

"""
Token 用量追踪
累加和查询对话过程中的 Token 消耗
"""

from ai_chat_cli.core.base.services import Service, ServiceKey


class TokenTracker:
    """Token 用量追踪器"""

    def __init__(self):
        self.total_tokens = 0
        self._logger = Service.get(ServiceKey.LOGGER)

    # ==================== 公共方法 ====================

    def track(self, usage):
        """
        累加 Token 用量

        Args:
            usage: OpenAI 返回的 usage 字典，含 prompt_tokens / completion_tokens / total_tokens
        """
        if not usage:
            return
        tokens = usage.get("total_tokens", 0)
        self.total_tokens += tokens
        self._logger.debug(
            f"本次 Token: 输入={usage.get('prompt_tokens', 0)}, "
            f"输出={usage.get('completion_tokens', 0)}, "
            f"累计={self.total_tokens}"
        )

    def get_total(self):
        """获取累计 Token 用量"""
        return self.total_tokens
