# -*- coding: utf-8 -*-

"""
模型定义
ModelType 枚举定义可用的 AI 模型及其绑定的 API 地址
Model 提供模型查询操作
"""

from enum import Enum


class ModelType(Enum):
    """
    可用模型列表
    每个枚举值为 (model_name, base_url) 元组
    """
    KIMI_K2_5 = ("kimi-k2.5", "https://api.moonshot.cn/v1")

    @property
    def model_name(self):
        """模型名称（传给 API 的值）"""
        return self.value[0]

    @property
    def base_url(self):
        """模型对应的 API 地址"""
        return self.value[1]


class Model:
    """
    模型注册表（纯静态方法，无需实例化）
    提供模型查询、列举等操作
    """

    @staticmethod
    def from_name(name):
        """
        根据模型名称查找枚举值

        Args:
            name: 模型名称字符串（如 "kimi-k2.5"）

        Returns:
            ModelType: 对应的枚举值

        Raises:
            ValueError: 未找到匹配的模型
        """
        for m in ModelType:
            if m.model_name == name:
                return m
        raise ValueError(f"未知模型: {name}，可选: {Model.list_names()}")

    @staticmethod
    def list_names():
        """返回所有可用模型名称列表"""
        return [m.model_name for m in ModelType]
