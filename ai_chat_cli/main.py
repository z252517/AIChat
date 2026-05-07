#!/usr/bin/env python
# encoding: utf-8

"""
程序入口
负责创建服务实例、注册到 Service，然后启动多轮对话主循环
"""

from ai_chat_cli.core.chat.chat_client import ChatClient
from ai_chat_cli.core.base.models import ModelType, Model
from ai_chat_cli.core.base.services import Service, ServiceKey
from ai_chat_cli.core.base.settings import Settings
from ai_chat_cli.core.base.logger import Logger
from ai_chat_cli.cli.display import Display
from ai_chat_cli.cli.commands import CommandHandler, CommandResult
from ai_chat_cli.tools.tool_manager import ToolManager


# ============ 主入口 ============

def _create_client():
    """根据当前配置创建并初始化 ChatClient"""
    settings = Settings.get_instance()
    client = ChatClient(
        api_key=settings.API_KEY,
        base_url=settings.BASE_URL,
    )
    client.set_model(settings.MODEL)
    client.set_system_prompt(settings.SYSTEM_PROMPT)
    tool_map = ToolManager.get_instance().load_tools()
    client.register_tools(tool_map)
    return client


def _setup_wizard(display):
    """
    首次启动引导向导（阶段式强制引导）

    Returns:
        bool: True 完成设置，False 用户中断退出
    """
    settings = Settings.get_instance()
    display.banner("欢迎使用 AI Chat CLI，请完成初始设置")

    # ========== 阶段一：选择模型 ==========
    if not settings.is_model_set():
        models = list(ModelType)
        options = [(m.model_name, m) for m in models]

        while True:
            display.show_selection("请选择模型:", options)
            choice = display.input_prompt("\n请输入编号: ")
            if choice is None:
                return False
            try:
                idx = int(choice)
                if 1 <= idx <= len(options):
                    selected_model = options[idx - 1][1]
                    settings.set_model(selected_model)
                    display.info(f"模型已设置: {selected_model.model_name}")
                    break
                else:
                    display.info(f"请输入 1~{len(options)} 之间的数字")
            except ValueError:
                display.info("请输入有效的编号数字")

    # ========== 阶段二：设置 API Key ==========
    if not settings.is_api_key_set():
        print()
        while True:
            api_key = display.input_prompt("请输入 API Key: ")
            if api_key is None:
                return False
            if api_key:
                settings.set_api_key(api_key)
                display.info(f"API Key 已设置 (尾号 ...{api_key[-6:]})")
                break
            else:
                display.info("API Key 不能为空")

    return True


def main():
    settings = Settings.get_instance()

    # 1. 注册全局服务
    Service.register(ServiceKey.DISPLAY, Display())
    Service.register(ServiceKey.LOGGER, Logger(
        show_timestamp=settings.LOG_SHOW_TIMESTAMP,
        log_file=settings.LOG_FILE,
    ))

    display = Service.get(ServiceKey.DISPLAY)

    # 2. 首次启动引导（强制完成）
    if not settings.is_model_set() or not settings.is_api_key_set():
        if not _setup_wizard(display):
            display.goodbye()
            return

    # 3. 创建客户端
    client = _create_client()

    # 4. 进入对话
    display.banner("AI 多轮对话模式 (输入 /help 查看命令)")
    display.info(f"当前模型: {settings.MODEL.model_name}")

    while True:
        user_input = display.user_prompt()

        if user_input is None:
            break

        if not user_input:
            continue

        action = CommandHandler.handle(user_input, client)
        if action == CommandResult.EXIT:
            break
        if action == CommandResult.HANDLED:
            continue

        try:
            display.ai_prefix()
            client.chat(user_input)
            display.ai_end()
        except Exception as e:
            display.error(e)


if __name__ == "__main__":
    main()