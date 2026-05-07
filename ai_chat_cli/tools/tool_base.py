from abc import ABC, abstractmethod


class ToolBase(ABC):
    """Tool 基类，子类必须实现 name/description/parameters 属性和 execute 方法"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述，告诉大模型这个工具的用途"""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """工具参数，OpenAI function calling 的 parameters JSON Schema"""
        ...

    @abstractmethod
    def execute(self, **kwargs):
        """执行工具逻辑，子类必须实现"""
        ...

    def to_tool_dict(self) -> dict:
        """将工具转换为 OpenAI function calling 格式的字典"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }