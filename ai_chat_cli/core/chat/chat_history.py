# -*- coding: utf-8 -*-

"""
对话历史管理
负责消息列表的维护、持久化和加载
"""

import json
import os
from datetime import datetime

from ai_chat_cli.core.base.services import Service, ServiceKey
from ai_chat_cli.core.base.settings import Settings


class ChatHistory:
    """对话历史管理器"""

    def __init__(self):
        self.messages = []
        self._logger = Service.get(ServiceKey.LOGGER)

    # ==================== 消息操作 ====================

    def append(self, message):
        """追加一条消息"""
        self.messages.append(message)

    def clear(self):
        """清空消息历史（保留系统提示词）"""
        if self.messages and self.messages[0]["role"] == "system":
            system_msg = self.messages[0]
            self.messages.clear()
            self.messages.append(system_msg)
        else:
            self.messages.clear()
        self._logger.info("对话历史已清空")

    # ==================== 持久化 ====================

    def save(self, filename=None):
        """
        保存对话历史到 JSON 文件

        Returns:
            str: 保存的文件路径
        """
        save_dir = Settings.get_instance().HISTORY_SAVE_DIR
        os.makedirs(save_dir, exist_ok=True)

        if not filename:
            filename = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(save_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.messages, f, ensure_ascii=False, indent=2)

        self._logger.info(f"对话历史已保存: {filepath}")
        return filepath

    def load(self, filepath):
        """
        从 JSON 文件加载对话历史

        Returns:
            bool: 是否加载成功
        """
        if not os.path.exists(filepath):
            self._logger.error(f"文件不存在: {filepath}")
            return False
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.messages.clear()
            self.messages.extend(loaded)
            self._logger.info(f"对话历史已加载: {filepath} ({len(self.messages)} 条消息)")
            return True
        except (json.JSONDecodeError, IOError, OSError) as e:
            self._logger.error(f"加载对话历史失败: {e}")
            return False
