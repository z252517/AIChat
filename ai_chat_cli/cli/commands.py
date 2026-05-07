# -*- coding: utf-8 -*-

"""
CLI 命令处理
解析和执行用户在终端中输入的特殊命令
"""

import os
import glob
from enum import Enum
from ai_chat_cli.core.base.settings import Settings
from ai_chat_cli.core.base.models import ModelType, Model
from ai_chat_cli.core.base.services import Service, ServiceKey


class CommandResult(Enum):
    """命令处理结果（与 CommandHandler 配套使用）"""
    EXIT = "exit"           # 退出程序
    HANDLED = "handled"     # 命令已处理，继续下一轮
    NONE = "none"           # 非命令，走正常对话流程


class CommandHandler:
    """
    命令处理器（纯静态方法，无需实例化）
    解析和执行用户在终端中输入的特殊命令
    """

    # 精确匹配命令 → 处理方法名
    # 方法签名: (cmd, client, display) -> CommandResult
    _EXACT_COMMANDS = {
        "/exit":    "_cmd_exit",
        "exit":     "_cmd_exit",
        "quit":     "_cmd_exit",
        "/quit":    "_cmd_exit",
        "/help":    "_cmd_help",
        "help":     "_cmd_help",
        "/clear":   "_cmd_clear",
        "clear":    "_cmd_clear",
        "/history": "_cmd_history",
        "history":  "_cmd_history",
        "/save":    "_cmd_save",
        "save":     "_cmd_save",
        "/tokens":  "_cmd_tokens",
        "tokens":   "_cmd_tokens",
    }

    # 前缀匹配命令 → 处理方法名（按优先级排列）
    _PREFIX_COMMANDS = [
        ("/setkey",  "_cmd_setkey"),
        ("setkey",   "_cmd_setkey"),
        ("/setmodel","_cmd_setmodel"),
        ("setmodel", "_cmd_setmodel"),
        ("/load",    "_cmd_load"),
        ("load",     "_cmd_load"),
        ("/rag",     "_cmd_rag"),
        ("rag",      "_cmd_rag"),
    ]

    # ==================== 入口 ====================

    @staticmethod
    def handle(command, client):
        """
        处理特殊命令

        Args:
            command: 用户输入的命令字符串
            client: ChatClient 实例

        Returns:
            CommandResult: 命令处理结果
        """
        cmd = command.strip()
        cmd_lower = cmd.lower()
        display = Service.get(ServiceKey.DISPLAY)

        # 精确匹配
        method_name = CommandHandler._EXACT_COMMANDS.get(cmd_lower)
        if method_name:
            method = getattr(CommandHandler, method_name)
            return method(cmd, client, display)

        # 前缀匹配
        for prefix, method_name in CommandHandler._PREFIX_COMMANDS:
            if cmd_lower.startswith(prefix):
                method = getattr(CommandHandler, method_name)
                return method(cmd, client, display)

        return CommandResult.NONE

    # ==================== 基础命令 ====================

    @staticmethod
    def _cmd_exit(cmd, client, display):
        display.goodbye()
        return CommandResult.EXIT

    @staticmethod
    def _cmd_help(cmd, client, display):
        display.show_help()
        return CommandResult.HANDLED

    @staticmethod
    def _cmd_clear(cmd, client, display):
        client.clear_history()
        display.info("已清空对话历史，上下文已重置")
        return CommandResult.HANDLED

    @staticmethod
    def _cmd_history(cmd, client, display):
        display.show_history(client.messages)
        return CommandResult.HANDLED

    @staticmethod
    def _cmd_save(cmd, client, display):
        filepath = client.save_history()
        display.info(f"对话历史已保存: {filepath}")
        return CommandResult.HANDLED

    @staticmethod
    def _cmd_tokens(cmd, client, display):
        display.info(f"累计 Token 用量: {client.get_token_usage()}")
        return CommandResult.HANDLED

    # ==================== 配置命令 ====================

    @staticmethod
    def _cmd_setkey(cmd, client, display):
        """处理 /setkey <api_key>"""
        settings = Settings.get_instance()
        parts = cmd.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            display.info("用法: /setkey <你的 API Key>")
            return CommandResult.HANDLED
        api_key = parts[1].strip()
        settings.set_api_key(api_key)
        if client:
            client.set_api_key(api_key)
        display.info(f"API Key 已设置并保存 (尾号 ...{api_key[-6:]})")
        return CommandResult.HANDLED

    @staticmethod
    def _cmd_setmodel(cmd, client, display):
        """处理 /setmodel <model_name>"""
        settings = Settings.get_instance()
        parts = cmd.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            current = settings.MODEL.model_name if settings.MODEL else "未设置"
            display.info(f"当前模型: {current}")
            display.info(f"可选模型: {', '.join(Model.list_names())}")
            display.info("用法: /setmodel <模型名称>")
            return CommandResult.HANDLED
        model_name = parts[1].strip()
        try:
            model = Model.from_name(model_name)
            settings.set_model(model)
            if client:
                client.set_model(model)
            display.info(f"模型已切换为: {model.model_name} (API: {model.base_url})")
        except ValueError:
            display.info(f"未知模型: {model_name}，可选: {', '.join(Model.list_names())}")
        return CommandResult.HANDLED

    # ==================== 历史加载命令 ====================

    @staticmethod
    def _cmd_load(cmd, client, display):
        """处理 /load [filename]"""
        settings = Settings.get_instance()
        parts = cmd.split(maxsplit=1)
        if len(parts) < 2:
            # 无参数：列出可用历史文件
            if os.path.exists(settings.HISTORY_SAVE_DIR):
                files = sorted(glob.glob(os.path.join(settings.HISTORY_SAVE_DIR, "*.json")))
                display.show_files(files, os.path.basename)
            else:
                display.show_files([], os.path.basename)
            return CommandResult.HANDLED
        filepath = os.path.join(settings.HISTORY_SAVE_DIR, parts[1])
        if not filepath.endswith(".json"):
            filepath += ".json"
        # 路径安全校验：防止路径遍历
        resolved = os.path.normcase(os.path.realpath(filepath))
        allowed = os.path.normcase(os.path.realpath(settings.HISTORY_SAVE_DIR))
        if not resolved.startswith(allowed + os.sep):
            display.info("错误：路径超出允许范围")
            return CommandResult.HANDLED
        if client.load_history(resolved):
            display.info(f"对话历史已加载: {filepath}")
        else:
            display.info(f"加载失败: {filepath}")
        return CommandResult.HANDLED

    # ==================== RAG 命令组 ====================

    @staticmethod
    def _cmd_rag(cmd, client, display):
        """处理 /rag <sub_command>"""
        parts = cmd.split()
        sub_cmd = parts[1].lower() if len(parts) > 1 else ""

        rag_handlers = {
            "status": CommandHandler._rag_status,
            "add":    CommandHandler._rag_add,
            "topics": CommandHandler._rag_topics,
            "clear":  CommandHandler._rag_clear,
        }

        handler = rag_handlers.get(sub_cmd)
        if handler:
            return handler(parts, display)

        display.show_rag_help()
        return CommandResult.HANDLED

    @staticmethod
    def _get_rag_manager():
        """延迟导入并获取 RAGManager 单例"""
        from ai_chat_cli.rag.rag_manager import RAGManager
        return RAGManager.get_instance()

    @staticmethod
    def _rag_status(parts, display):
        try:
            manager = CommandHandler._get_rag_manager()
            topic = parts[2] if len(parts) > 2 else None
            stats = manager.get_stats(topic)
            if topic:
                display.show_rag_topic_stats(topic, stats)
            else:
                display.show_rag_global_stats(stats)
        except Exception as e:
            display.info(f"获取状态失败: {e}")
        return CommandResult.HANDLED

    @staticmethod
    def _rag_add(parts, display):
        if len(parts) < 3:
            display.info("用法: /rag add <文件路径> [主题]")
            return CommandResult.HANDLED
        file_path = parts[2]
        topic = parts[3] if len(parts) > 3 else None
        try:
            manager = CommandHandler._get_rag_manager()
            display.info(f"正在加载文件: {file_path}")
            result = manager.add_file(file_path, topic=topic)
            display.info(result["message"])
        except Exception as e:
            display.info(f"添加失败: {e}")
        return CommandResult.HANDLED

    @staticmethod
    def _rag_topics(parts, display):
        try:
            manager = CommandHandler._get_rag_manager()
            topics = manager.list_topics()
            topic_list = []
            for t in topics:
                stats = manager.get_stats(t)
                topic_list.append((t, stats['total_chunks'], stats['source_count']))
            display.show_rag_topics(topic_list)
        except Exception as e:
            display.info(f"获取主题列表失败: {e}")
        return CommandResult.HANDLED

    @staticmethod
    def _rag_clear(parts, display):
        try:
            manager = CommandHandler._get_rag_manager()
            topic = parts[2] if len(parts) > 2 else None
            manager.clear(topic)
            if topic:
                display.info(f"已清空主题 '{topic}' 的知识库")
            else:
                display.info("已清空所有知识库")
        except Exception as e:
            display.info(f"清空失败: {e}")
        return CommandResult.HANDLED