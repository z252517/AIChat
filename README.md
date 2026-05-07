# AI Chat CLI

支持多模型的多轮对话命令行应用，支持流式输出、思考过程展示、工具调用（Function Calling）、RAG 知识库等特性。

## 功能特性

- **多轮对话** — 支持上下文连续对话
- **思考过程** — 实时展示模型思考链（Reasoning）
- **工具调用** — 内置网页搜索、获取时间、代码执行、文件读写等工具，支持自定义扩展
- **RAG 知识库** — 加载本地文档（TXT/MD/PDF）构建知识库，支持多主题分类，密集 + 混合检索（ChromaDB + BM25 + RRF 融合）
- **流式输出** — 逐字输出回复，体验流畅
- **自动重试** — 请求失败自动重试
- **对话管理** — 保存/加载对话历史
- **彩色终端** — 不同信息区间以不同颜色区分
- **持久配置** — API Key 和模型设置一次后自动记忆

## 快速开始

**环境要求**：Python >= 3.8

### 安装

```bash
git clone https://github.com/z252517/AIChat.git
cd AIChat
pip install -e .                        # 基础安装（含 RAG 密集检索）
pip install -e ".[rag-hybrid]"          # 额外安装混合检索（BM25 + jieba）
```

### 启动

```bash
ai-chat                                 # 控制台脚本（需先 pip install）
python -m ai_chat_cli                   # 模块运行
python ai_chat_cli/main.py              # 直接运行（需先安装依赖）
```

首次启动会通过交互式向导引导完成模型选择和 API Key 设置，配置自动保存至 `~/.ai-chat-cli/user_config.yaml`。

## 使用命令

| 命令 | 说明 |
|------|------|
| `/setkey <Key>` | 设置 API Key（持久保存） |
| `/setmodel` | 查看/切换模型（持久保存） |
| `/help` | 显示帮助信息 |
| `/exit` | 退出程序 |
| `/clear` | 清空对话历史 |
| `/history` | 查看对话历史 |
| `/save` | 保存对话历史 |
| `/load` | 列出/加载已保存的历史文件 |
| `/tokens` | 查看 Token 用量 |
| `/rag` | RAG 知识库管理帮助 |
| `/rag status [主题]` | 查看知识库状态 |
| `/rag add <文件> [主题]` | 添加文件到知识库 |
| `/rag topics` | 列出所有主题 |
| `/rag clear [主题]` | 清空知识库 |

## RAG 知识库

RAG（检索增强生成）功能让 AI 可以基于你的本地文档进行回答。

### 安装依赖

```bash
pip install -e .                        # 基础安装已含 RAG（ChromaDB + PyMuPDF）
pip install -e ".[rag-hybrid]"          # 额外安装混合检索（BM25 + jieba）
```

### 使用方式

```bash
# 方式一：通过命令手动添加文档
/rag add D:/docs/manual.pdf tech

# 方式二：对话中让 AI 自动调用
你: 帮我把 D:/notes/guide.md 加入知识库，主题是 tutorial
AI: 成功添加 15 个文档片段

# 基于知识库提问（AI 自动检索）
你: 这个手册中关于安装步骤怎么说的？
AI: 根据手册内容，安装步骤如下...
```

### 多主题管理

知识库支持按主题分类存储，不同领域的文档互不干扰：

```
/rag add report.pdf finance    # 添加到 finance 主题
/rag add manual.md tech        # 添加到 tech 主题
/rag add notes.txt             # 添加到 default 主题
/rag topics                    # 查看所有主题
/rag clear finance             # 只清空 finance 主题
```

### 检索模式

| 模式 | 组件 | 条件 |
|------|------|------|
| 密集检索 | ChromaDB embedding | 始终可用 |
| 混合检索 | ChromaDB + BM25 + RRF 融合 | 安装 `rank-bm25` 时自动启用 |

## 自定义工具

1. 在 `ai_chat_cli/tools/builtin/` 目录下新建 Python 文件
2. 继承 `ToolBase` 基类，实现 `name`、`description`、`parameters`、`execute`
3. 在 `ai_chat_cli/config/tools.yaml` 中添加工具类路径即可启用

示例参考：`ai_chat_cli/tools/builtin/get_current_time.py`

## 架构设计

```
┌─────────────────────────────────────────────────┐
│                   main.py                       │  程序入口
├─────────────────────────────────────────────────┤
│      cli/commands        cli/display            │  交互层
├─────────────────────────────────────────────────┤
│   core/chat/chat_session  core/chat/streaming    │  业务层
├────────────────┬────────────────┬────────────────┤
│   tools/       │    rag/        │   config/      │  功能模块
│   tool_manager │    rag_manager │   *.yaml       │
│   builtin/*    │    hybrid_searcher              │
├────────────────┴────────────────┴────────────────┤
│   core/base/  settings | services | models       │  基础设施
│               logger                             │
└─────────────────────────────────────────────────┘
```

**核心设计原则：**
- 管理类采用单例模式（Settings、ToolManager、RAGManager）
- 服务注册中心（Service）解耦模块间依赖
- 命令处理采用路由表驱动，新增命令无需改动分发逻辑
- 工具系统通过 YAML 配置 + `importlib` 动态加载，即插即用

## 项目结构

```
ai_chat_cli/
├── main.py                  # 程序入口
├── config/                  # YAML 配置文件
│   ├── app.yaml             # 通用配置（重试、工具循环、workspace）
│   ├── prompts.yaml         # 系统提示词
│   ├── rag.yaml             # RAG 配置（分块大小、top_k）
│   └── tools.yaml           # 工具注册表
├── core/
│   ├── base/                # 基础设施（配置、模型、服务、日志）
│   └── chat/                # 聊天业务（客户端、流式处理）
├── cli/                     # 命令行交互（命令路由、终端显示）
├── rag/                     # RAG 知识库
│   ├── document_loader      # 文档加载（TXT/MD/PDF）
│   ├── text_splitter        # 智能分块
│   ├── vector_store         # ChromaDB 密集存储
│   ├── sparse_store         # BM25 稀疏索引
│   ├── hybrid_searcher      # 密集 + 稀疏 RRF 融合检索
│   └── rag_manager          # 门面管理器
└── tools/                   # 工具系统
    ├── tool_base            # 抽象基类
    ├── tool_manager         # 动态加载器
    └── builtin/             # 6 个内置工具
```

用户数据存放在 `~/.ai-chat-cli/`（运行后自动生成）：

```
~/.ai-chat-cli/
├── user_config.yaml         # 用户配置（API Key、模型选择）
├── logs/                    # 运行日志
├── chat_history/            # 对话历史存档
├── knowledge_base/          # RAG 向量库数据
└── workspace/               # 文件工具沙箱目录
```

## 构建可执行文件

```bash
pyinstaller ai-chat.spec                # 单文件 .exe
pyinstaller ai-chat-dir.spec            # 目录模式
```

## 许可证

MIT License
