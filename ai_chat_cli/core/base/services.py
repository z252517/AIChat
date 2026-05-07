# -*- coding: utf-8 -*-

"""
服务注册中心
使用 Service 类统一管理全局服务实例的注册与获取
外部模块在启动时注册具体实现，内部通过 get 方法使用
"""

from enum import Enum


class ServiceKey(Enum):
    """服务标识枚举，避免手写字符串"""
    DISPLAY = "display"
    LOGGER = "logger"


class Service:
    """
    全局服务注册中心（类级别存储，无需实例化）
    所有服务通过 register / get 统一管理

    用法:
        Service.register(ServiceKey.DISPLAY, Display())
        display = Service.get(ServiceKey.DISPLAY)
    """

    _services = {}

    @classmethod
    def register(cls, key, instance):
        """
        注册一个服务实例

        Args:
            key: ServiceKey 枚举值或字符串
            instance: 服务实例
        """
        name = key.value if isinstance(key, ServiceKey) else key
        cls._services[name] = instance

    @classmethod
    def get(cls, key):
        """
        获取已注册的服务实例

        Args:
            key: ServiceKey 枚举值或字符串

        Returns:
            对应的服务实例

        Raises:
            RuntimeError: 如果服务尚未注册
        """
        name = key.value if isinstance(key, ServiceKey) else key
        if name not in cls._services:
            raise RuntimeError(f"服务 '{name}' 未注册，请先调用 Service.register()")
        return cls._services[name]
