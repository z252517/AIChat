# 项目架构

## 目录结构

```
ai_chat_cli/
├── __init__.py
├── __main__.py              # python -m 入口
├── main.py                  # 主入口：启动向导、REPL 循环
├── config/                  # YAML 配置文件
│   ├── app.yaml             # 重试、工具调用、workspace、日志、历史记录
│   ├── prompts.yaml         # 系统提示词模板
│   ├── rag.yaml             # 分块大小、top_k、ChromaDB 目录
│   └── tools.yaml           # 工具注册表（类路径列表）
├── core/
│   ├── base/
│   │   ├── settings.py      # 单例配置管理器
│   │   ├── models.py        # ModelType 枚举 + 模型注册表
│   │   ├── services.py      # 服务定位器（依赖注入）
│   │   └── logger.py        # 文件日志
│   └── chat/
│       ├── chat_client.py   # 门面，组合各子模块
│       ├── chat_session.py  # ReAct 工具调用循环及三层防护
│       ├── chat_config.py   # 工具注册与配置
│       ├── chat_history.py  # 消息历史管理
│       ├── request_sender.py # OpenAI API 通信
│       ├── tool_executor.py # 工具执行编排
│       ├── token_tracker.py # Token 用量统计
│       └── streaming.py     # SSE 流解析器 + 加载动画
├── cli/
│   ├── commands.py          # 表驱动路由的斜杠命令处理
│   └── display.py           # ANSI 彩色终端输出
├── rag/
│   ├── document_loader.py   # TXT/MD/PDF 加载
│   ├── text_splitter.py     # 智能分块（含 chunk_id 注入）
│   ├── vector_store.py      # ChromaDB 封装（UUID 文档 ID）
│   ├── sparse_store.py      # BM25 稀疏索引
│   ├── hybrid_searcher.py   # 密集+稀疏 RRF 融合搜索
│   └── rag_manager.py       # 门面模式管理器
└── tools/
    ├── tool_base.py         # 工具抽象基类
    ├── tool_manager.py      # 动态工具加载器
    └── builtin/             # 内置工具
        ├── web_search.py
        ├── get_current_time.py
        ├── code_executor.py
        ├── file_rw.py
        ├── knowledge_store.py
        └── knowledge_search.py
```

## 核心设计模式

### 单例模式

`Settings`、`ToolManager`、`RAGManager` 均采用单例模式，通过 `get_instance()` 类方法获取唯一实例：

```python
class Settings:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
```

### 服务定位器

`core/base/services.py` 中的 `Service` 类提供全局依赖注入。通过 `Service.get(ServiceKey.LOGGER)` / `Service.set(ServiceKey.LOGGER, instance)` 注册和获取服务实例。

### 命令路由

斜杠命令使用表驱动路由，添加新命令无需修改分发逻辑：

```python
_EXACT_COMMANDS = {"/help": "_handle_help", "/exit": "_handle_exit", ...}
_PREFIX_COMMANDS = [("/model ", "_handle_set_model"), ...]
```

### 工具系统（即插即用）

1. 继承 `ToolBase`，实现 `name`、`description`、`parameters` 属性和 `execute()` 方法
2. 在 `config/tools.yaml` 中注册类路径
3. `ToolManager` 启动时动态导入并实例化

### 门面模式

`RAGManager` 封装 `DocumentLoader` → `TextSplitter` → `VectorStore` + `SparseStore` 的完整流程，对工具和命令提供统一高层 API。

## 配置加载

配置三层来源：

| 层级 | 路径 | 性质 |
|------|------|------|
| 包内默认配置 | `config/*.yaml` | 只读，随包分发 |
| 用户配置 | `~/.ai-chat-cli/user_config.yaml` | 读写，持久化用户选择 |
| 内存默认值 | `Settings.__init__()` 硬编码 | 当 YAML 键缺失时的回退值 |

`Settings._load_all()` 按顺序加载：`app.yaml` → `prompts.yaml` → `rag.yaml` → `tools.yaml` → `user_config.yaml`。

## RAG 检索模式

| 模式 | 组件 | 条件 |
|------|------|------|
| 稠密检索 | ChromaDB embedding | 始终可用 |
| 混合检索 | ChromaDB + BM25 + RRF 融合 | `rank-bm25` 已安装时自动启用 |

`RAGManager` 在 `__init__` 中检测 `rank-bm25` 可用性，确定检索模式。混合检索的 RRF 去重使用 `chunk_id` 字段，详见下方"文档 ID 策略"。

### 数据一致性策略

混合检索的稠密存储（ChromaDB）和稀疏存储（BM25 JSON）采用"最终一致性"策略：
- 稀疏写入失败时记录警告但不中断流程，允许短暂不一致
- 稀疏索引采用 lazy rebuild 策略，`add_documents` 只标记 dirty，`search` 时才重建
- 不一致仅影响检索质量（召回率），不会丢失数据

## 文档 ID 策略

- **入库 ID**：ChromaDB 文档 ID 使用 `uuid.uuid4().hex`，纯 UUID，无计数器，防止删除/重入库冲突
- **分块 ID**：`text_splitter.py` 在每个 chunk 的 metadata 中注入 `chunk_id`（`uuid.uuid4().hex`），同时写入 VectorStore 和 SparseStore
- **RRF 去重**：`hybrid_searcher.py` 以 `chunk_id` 为 key 匹配两路结果，避免重叠分块内容相同时被错误合并
- **旧数据兼容**：`chunk_id` 为空时降级回 `content`
