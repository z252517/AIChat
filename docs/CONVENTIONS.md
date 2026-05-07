# 编码规范

> 基于项目现有代码提炼的规范，所有贡献者必须遵守。

## 名称约定

| 类别 | 规则 | 示例 |
|------|------|------|
| 类名 | `PascalCase`；内部类加 `_` 前缀 | `ChatClient`、`_StreamResult` |
| 方法名 | `snake_case`；私有方法 `_` 前缀 | `get_instance()`、`_send()` |
| 变量 | `snake_case`；私有属性 `_` 前缀 | `self.total_tokens`、`self._client` |
| 常量 | `UPPER_SNAKE_CASE` | `DEFAULT_TOPIC`、`MAX_RETRIES`、`_EXECUTION_TIMEOUT` |
| 模块文件 | `snake_case` | `vector_store.py`、`code_executor.py` |
| 属性 | `snake_case` | `self.name`、`self.description`、`self.parameters` |
| 枚举值 | `UPPER_SNAKE_CASE` | `KIMI_K2_5`、`EXIT` |

## 代码风格

### 编码声明

所有包含中文的文件必须以 `# -*- coding: utf-8 -*-` 开头。

### 注释语言

中文为主，技术术语（API、Token、RAG、BM25、ChromaDB 等）保留英文。文档字符串使用中文。

### 文档字符串

```python
"""类/模块用途描述"""

def method(self, arg1, arg2):
    """
    方法用途描述

    Args:
        arg1: 参数说明
        arg2: 参数说明

    Returns:
        返回值说明
    """
```

### 类内分组

用分隔注释将方法分为逻辑区域。区域从 `__init__` 开始，先公共后私有：

```python
class SomeClass:
    # ==================== 常量 ====================

    # ==================== 单例 ====================
    @classmethod
    def get_instance(cls): ...

    # ==================== 初始化 ====================
    def __init__(self): ...

    # ==================== 公共方法 ====================
    def public_api(self): ...

    # ==================== 内部方法 ====================
    def _private_method(self): ...
```

标签格式：`全角等号`，如 `# ==================== 公共方法 ====================`。

### 多行字符串

长字符串使用括号隐式拼接，每行独立的中文语义单元：

```python
return (
    "错误: 文件路径必须在 workspace 目录内\n"
    f"  workspace: {workspace}\n"
    f"  请求路径: {resolved}"
)
```

### 多行列表/结果构建

用列表 `append()` 后 `"\n".join()`，不用逐行 `+=`：

```python
lines = []
lines.append("标题")
lines.append(item_info)
return "\n".join(lines)
```

## 导入规则

### 导入顺序

1. `# -*- coding: utf-8 -*-`
2. 模块文档字符串
3. 空行
4. 标准库导入
5. 第三方库导入
6. 项目内导入（`from ai_chat_cli.*`）

各组之间不空行，组之间空一行。

### 绝对导入

**只允许绝对导入**。不允许 `from . import` 相对导入：

```python
# 正确
from ai_chat_cli.tools.tool_base import ToolBase
from ai_chat_cli.core.base.settings import Settings

# 禁止
from .tool_base import ToolBase
from ..core.base.settings import Settings
```

### 延迟导入

可选依赖或避免循环引用时，在方法体内导入：

```python
def execute(self, **kwargs):
    from ddgs import DDGS          # 可选依赖
    from ai_chat_cli.rag.rag_manager import RAGManager  # 避免循环
```

## 错误处理

### 工具 execute() 方法

捕获异常，返回错误字符串，**不抛出**异常：

```python
def execute(self, **kwargs):
    try:
        return do_work()
    except Exception as e:
        return f"操作失败: {str(e)}"
```

### 业务逻辑方法

按异常粒度从具体到一般依次捕获：

```python
try:
    # ...
except FileNotFoundError as e:
    return self._result(False, f"文件不存在: {e}")
except ValueError as e:
    return self._result(False, f"格式错误: {e}")
except Exception as e:
    return self._result(False, f"操作失败: {e}")
```

### 可选依赖

```python
try:
    import chromadb
except ImportError:
    raise ImportError("RAG 功能需要 chromadb 库，请运行: pip install chromadb")
```

静默降级：

```python
try:
    from ai_chat_cli.rag.sparse_store import SparseStore
    self._sparse_store = SparseStore(...)
except ImportError:
    pass  # 可选依赖不可用，降级
```

### 重试循环

```python
for attempt in range(1, max_retries + 1):
    try:
        return do_request()
    except Exception as e:
        last_error = e
        if attempt < max_retries:
            time.sleep(delay)
raise last_error
```

## 配置约定

- 所有运行时配置通过 `Settings.get_instance()` 访问
- YAML 配置键在 `Settings.__init__()` 中有默认回退值
- 新增配置项步骤：
  1. 在 `config/app.yaml` 添加键
  2. 在 `Settings.__init__()` 添加默认值属性
  3. 添加 `_apply_*_config()` 方法并在 `_load_all()` 中调用
  4. 更新 `Settings` 的 `__init__.py` docstring 属性清单

## 工具开发规范

新工具必须：

1. 继承 `ToolBase`
2. 实现三个属性：`name` → `str`、`description` → `str`、`parameters` → `dict`（JSON Schema）
3. 实现 `execute(self, **kwargs)` 方法
4. 在 `config/tools.yaml` 注册类路径
5. 放在 `tools/builtin/` 目录下

```python
class MyTool(ToolBase):
    @property
    def name(self) -> str:
        return "my_tool"

    @property
    def description(self) -> str:
        return "工具用途描述"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {...},
            "required": [...],
        }

    def execute(self, **kwargs):
        ...
```

## 类型注解

**不强制要求**。现有项目仅在 `ToolBase` 属性返回值和少量关键方法上使用类型注解。未来逐步添加。

## 文件组织

- **一个文件一个主类**（相关类可同文件，如 `FileRead` 和 `FileWrite`）
- 辅助私有类与父类同文件（如 `_StreamResult` 与 `StreamHandler`）
- 模块级函数仅用于无状态的工具函数（如 `_resolve_safe_path`）
