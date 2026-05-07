# -*- coding: utf-8 -*-

"""
全局配置管理器（单例模式）

配置来源：
- 包内默认配置（config/*.yaml）：只读，随包分发
- 用户配置（~/.ai-chat-cli/user_config.yaml）：读写，持久化用户选择
- 用户数据目录（~/.ai-chat-cli/）：logs、chat_history 等运行时数据
"""

import os
import sys
import yaml
from ai_chat_cli.core.base.models import ModelType, Model


class Settings:
    """
    全局配置管理器

    属性分组：
    - 模型 & API：MODEL, API_KEY, BASE_URL, SYSTEM_PROMPT
    - 重试策略：MAX_RETRIES, RETRY_DELAY
    - 工具调用：MAX_TOOL_ROUNDS, TOOL_STALE_ROUNDS, TOOL_MAX_TOKENS
    - 日志：LOG_SHOW_TIMESTAMP, LOG_FILE
    - 文件操作沙箱：WORKSPACE_DIR
    - 工具：TOOL_CLASSES
    - 对话历史：HISTORY_SAVE_DIR
    - RAG 知识库：RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP, RAG_TOP_K, RAG_DB_DIR
    """

    _instance = None

    # ==================== 路径常量 ====================

    _USER_DATA_DIR_NAME = ".ai-chat-cli"
    _USER_CONFIG_FILE = "user_config.yaml"

    # ==================== 单例 ====================

    @classmethod
    def get_instance(cls):
        """获取全局单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ==================== 初始化 ====================

    def __init__(self, package_config_dir=None, user_data_dir=None):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True

        self._package_config_dir = package_config_dir or self._resolve_package_config_dir()
        self._user_data_dir = user_data_dir or self._resolve_user_data_dir()

        # -- 模型 & API --
        self.MODEL = None               # ModelType: 当前选用的模型枚举值
        self.API_KEY = ""               # str: API 密钥
        self.BASE_URL = ""              # str: 模型对应的 API 地址
        self.SYSTEM_PROMPT = ""         # str: 系统提示词

        # -- 重试策略 --
        self.MAX_RETRIES = 3            # int: 最大重试次数
        self.RETRY_DELAY = 1.0          # float: 重试间隔（秒）

        # -- 工具调用 --
        self.MAX_TOOL_ROUNDS = 20       # int: 单轮对话工具调用最大循环轮次（兜底）
        self.TOOL_STALE_ROUNDS = 3      # int: 连续相同工具调用视为死循环的阈值
        self.TOOL_MAX_TOKENS = 100000   # int: 单次对话工具调用累计 Token 上限

        # -- 日志 --
        self.LOG_SHOW_TIMESTAMP = True  # bool: 日志是否显示时间戳
        self.LOG_FILE = ""              # str: 日志文件路径（绝对路径）

        # -- 工具 --
        self.TOOL_CLASSES = []          # list[str]: 工具类路径列表

        # -- 对话历史 --
        self.HISTORY_SAVE_DIR = ""      # str: 对话历史保存目录（绝对路径）

        # -- 文件操作沙箱 --
        self.WORKSPACE_DIR = ""          # str: 文件读写白名单目录（绝对路径）

        # -- RAG 知识库 --
        self.RAG_CHUNK_SIZE = 500       # int: 文本分割块大小
        self.RAG_CHUNK_OVERLAP = 50     # int: 相邻块重叠字符数
        self.RAG_TOP_K = 3             # int: 检索返回结果数
        self.RAG_DB_DIR = ""            # str: 向量库存储目录（绝对路径）

        # 加载配置
        os.makedirs(self._user_data_dir, exist_ok=True)
        self._load_all()

    # ==================== 公共方法 ====================

    def set_api_key(self, api_key):
        """设置 API Key 并持久化"""
        self._update_user_config("api_key", api_key)
        self.API_KEY = api_key

    def set_model(self, model):
        """设置模型并持久化（同时更新 base_url）"""
        if not isinstance(model, ModelType):
            raise ValueError(f"无效的模型，可选: {Model.list_names()}")
        self._update_user_config("model", model.model_name)
        self.MODEL = model
        self.BASE_URL = model.base_url

    def is_api_key_set(self):
        """检查 API Key 是否已设置"""
        return bool(self.API_KEY)

    def is_model_set(self):
        """检查模型是否已设置"""
        return self.MODEL is not None

    def reload(self):
        """重新加载所有配置（热更新）"""
        self._load_all()

    # ==================== 内部：配置加载 ====================

    def _load_all(self):
        """加载全部配置文件并解析为属性"""
        app_config = self._load_package_yaml("app.yaml", required=True)
        prompts_config = self._load_package_yaml("prompts.yaml")
        rag_config = self._load_package_yaml("rag.yaml")
        tools_config = self._load_package_yaml("tools.yaml")
        user_config = self._load_user_config()

        self._apply_model_config(user_config)
        self._apply_prompt_config(prompts_config)
        self._apply_retry_config(app_config)
        self._apply_tool_config(app_config)
        self._apply_workspace_config(app_config)
        self._apply_logging_config(app_config)
        self._apply_history_config(app_config)
        self._apply_tools_config(tools_config)
        self._apply_rag_config(rag_config)

    def _apply_model_config(self, user_config):
        """解析模型 & API 配置"""
        model_str = user_config.get("model", "")
        try:
            self.MODEL = Model.from_name(model_str) if model_str else None
        except ValueError:
            self.MODEL = None
        self.API_KEY = user_config.get("api_key", "")
        self.BASE_URL = self.MODEL.base_url if self.MODEL else ""

    def _apply_prompt_config(self, prompts_config):
        """解析提示词配置"""
        self.SYSTEM_PROMPT = prompts_config.get("default", "").strip()

    def _apply_retry_config(self, app_config):
        """解析重试策略配置"""
        retry = app_config.get("retry", {})
        self.MAX_RETRIES = retry.get("max_retries", 3)
        self.RETRY_DELAY = retry.get("retry_delay", 1.0)

    def _apply_tool_config(self, app_config):
        """解析工具调用配置"""
        tool = app_config.get("tool", {})
        self.MAX_TOOL_ROUNDS = tool.get("max_rounds", 20)
        self.TOOL_STALE_ROUNDS = tool.get("stale_rounds", 3)
        self.TOOL_MAX_TOKENS = tool.get("max_tool_tokens", 100000)

    def _apply_workspace_config(self, app_config):
        """解析文件操作沙箱配置"""
        workspace = app_config.get("workspace", {})
        workspace_dir = workspace.get("dir", "workspace")
        self.WORKSPACE_DIR = os.path.join(self._user_data_dir, workspace_dir)
        os.makedirs(self.WORKSPACE_DIR, exist_ok=True)

    def _apply_logging_config(self, app_config):
        """解析日志配置"""
        logging_cfg = app_config.get("logging", {})
        self.LOG_SHOW_TIMESTAMP = logging_cfg.get("show_timestamp", True)
        log_file = logging_cfg.get("file", "logs/app.log")
        self.LOG_FILE = os.path.join(self._user_data_dir, log_file)

    def _apply_history_config(self, app_config):
        """解析对话历史配置"""
        save_dir = app_config.get("history", {}).get("save_dir", "chat_history")
        self.HISTORY_SAVE_DIR = os.path.join(self._user_data_dir, save_dir)

    def _apply_tools_config(self, tools_config):
        """解析工具配置"""
        self.TOOL_CLASSES = tools_config.get("tools", [])

    def _apply_rag_config(self, rag_config):
        """解析 RAG 知识库配置"""
        self.RAG_CHUNK_SIZE = rag_config.get("chunk_size", 500)
        self.RAG_CHUNK_OVERLAP = rag_config.get("chunk_overlap", 50)
        self.RAG_TOP_K = rag_config.get("top_k", 3)
        rag_db_dir = rag_config.get("db_dir", "knowledge_base")
        self.RAG_DB_DIR = os.path.join(self._user_data_dir, rag_db_dir)

    # ==================== 内部：YAML 读写 ====================

    def _load_package_yaml(self, filename, required=False):
        """
        加载包内配置文件

        Args:
            filename: yaml 文件名
            required: 是否必须存在，True 时文件缺失则抛异常
        """
        filepath = os.path.join(self._package_config_dir, filename)
        data = self._read_yaml(filepath)
        if data is None and required:
            raise FileNotFoundError(f"配置文件不存在: {filepath}")
        return data or {}

    def _load_user_config(self):
        """加载用户配置文件"""
        return self._read_yaml(self._user_config_path()) or {}

    def _update_user_config(self, key, value):
        """更新用户配置中的单个字段并保存"""
        config = self._load_user_config()
        config[key] = value
        with open(self._user_config_path(), "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    def _user_config_path(self):
        """用户配置文件完整路径"""
        return os.path.join(self._user_data_dir, self._USER_CONFIG_FILE)

    @staticmethod
    def _read_yaml(filepath):
        """读取 YAML 文件，不存在返回 None"""
        if not os.path.exists(filepath):
            return None
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    # ==================== 内部：路径解析 ====================

    @staticmethod
    def _resolve_package_config_dir():
        """解析包内配置目录路径（兼容 PyInstaller 打包）"""
        if getattr(sys, "frozen", False):
            return os.path.join(sys._MEIPASS, "ai_chat_cli", "config")
        # core/base/settings.py → 上两级到 ai_chat_cli/ → config/
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config"
        )

    @staticmethod
    def _resolve_user_data_dir():
        """解析用户数据目录路径"""
        return os.path.join(os.path.expanduser("~"), Settings._USER_DATA_DIR_NAME)