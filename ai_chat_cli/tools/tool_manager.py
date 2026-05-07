# -*- coding: utf-8 -*-

"""
工具管理器
负责工具的配置化加载、注册和管理
根据 config/tools.yaml 中的工具类路径列表，按需导入并实例化工具
新增工具只需在配置文件中添加一行路径，无需改动代码
"""

import importlib
from ai_chat_cli.tools.tool_base import ToolBase
from ai_chat_cli.core.base.services import Service, ServiceKey
from ai_chat_cli.core.base.settings import Settings


class ToolManager:
    """
    工具管理器（单例模式）
    负责工具的加载、注册和管理，后续可扩展工具热重载、状态查询等功能
    """

    _instance = None

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        self._tool_map = {}  # {tool_name: ToolBase 实例}

    @classmethod
    def get_instance(cls):
        """获取全局单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_tools(self):
        """
        根据配置加载工具实例

        从 tools.yaml 的 tools 列表中读取工具类路径（如 "tools.builtin.web_search.WebSearch"），
        逐个导入模块并实例化，存入内部 tool_map。

        Returns:
            dict: {tool_name: ToolBase 实例} 的字典
        """
        logger = Service.get(ServiceKey.LOGGER)
        self._tool_map = {}

        for class_path in Settings.get_instance().TOOL_CLASSES:
            try:
                # 拆分 "tools.builtin.web_search.WebSearch" → 模块路径 + 类名
                module_path, class_name = class_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)

                # 校验是否为 ToolBase 子类
                if not (isinstance(cls, type) and issubclass(cls, ToolBase) and cls is not ToolBase):
                    logger.warning(f"跳过 {class_path}: 不是有效的 ToolBase 子类")
                    continue

                instance = cls()
                self._tool_map[instance.name] = instance
                logger.debug(f"注册工具: {instance.name}")

            except Exception as e:
                logger.warning(f"加载工具 {class_path} 失败: {e}")

        logger.info(f"已加载 {len(self._tool_map)} 个工具: {list(self._tool_map.keys())}")
        return self._tool_map

    def get_tool_map(self):
        """获取已加载的工具映射表"""
        return self._tool_map

    def get_tool(self, name):
        """
        根据名称获取工具实例

        Args:
            name: 工具名称

        Returns:
            ToolBase: 工具实例，未找到返回 None
        """
        return self._tool_map.get(name)

    def list_tool_names(self):
        """获取所有已加载的工具名称列表"""
        return list(self._tool_map.keys())
