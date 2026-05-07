# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
pip install -e .                        # 开发安装
pip install -e ".[rag-hybrid]"          # 带 RAG 支持

ai-chat                                 # 启动（控制台脚本）
python -m ai_chat_cli                   # 启动（模块运行）

pyinstaller ai-chat.spec                # 构建单文件 .exe
pyinstaller ai-chat-dir.spec            # 构建目录模式
```

无测试框架、无 linter、无类型检查。

## Architecture

四层：Infrastructure (`core/base/`) → Business (`core/chat/`) → Capability (`tools/`, `rag/`) → Interaction (`cli/`)

入口：`ai_chat_cli/main.py` → 注册服务 → 初始化配置 → 加载工具 → REPL 循环

## Key Patterns

| 模式 | 位置 | 说明 |
|------|------|------|
| 单例 | `Settings`, `ToolManager`, `RAGManager` | `get_instance()` 类方法 |
| 服务定位器 | `core/base/services.py` | `Service.register()` / `Service.get()` |
| 表驱动路由 | `cli/commands.py` | `_EXACT_COMMANDS` dict + `_PREFIX_COMMANDS` list |
| 插件工具 | `config/tools.yaml` + `tool_manager.py` | `importlib` 动态导入 |
| ReAct 循环 | `core/chat/chat_session.py` | tool_calls → 执行 → 回传 → 重复，三层防护 |
| 配置三层加载 | `core/base/settings.py` | 包内 YAML → 用户 YAML → 硬编码默认值 |

## Code Conventions

- Claude Code 交流：思考和回复用中文，学术、专业、项目名词保留英文
- 含中文文件以 `# -*- coding: utf-8 -*-` 开头，注释用中文
- **只允许绝对导入**，禁止相对导入
- 可选依赖延迟导入（方法体内 import）
- 类内分隔注释：`# ==================== 公共方法 ====================`
- 工具属性 snake_case：`name`, `description`, `parameters`
- 工具 `execute()` 返回错误字符串，不抛异常

## Tool Development

继承 `ToolBase` → 实现 `name`/`description`/`parameters` + `execute()` → 注册到 `config/tools.yaml` → 放入 `tools/builtin/`

## Docs Reference

| 文档 | 内容 |
|------|------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 目录结构、设计模式代码示例、配置加载流程、RAG 检索模式、文档 ID 策略 |
| [docs/CONVENTIONS.md](docs/CONVENTIONS.md) | 命名规范、代码风格、导入规则、错误处理模式、工具开发规范、新增配置步骤 |
| [docs/SECURITY.md](docs/SECURITY.md) | 代码执行沙箱、文件操作沙箱、工具调用循环防护（含配置项） |
| [docs/ISSUES.md](docs/ISSUES.md) | 问题清单（P0-P3）与修复记录 |
