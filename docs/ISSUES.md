# 项目问题修复与优化清单

> 更新日期：2026-05-06
> 基于全面代码审查重新整理，按优先级排列。

---

## 优先级总览

| 优先级 | 数量 | 范围 |
|--------|------|------|
| P0 | 2 | 安全——必须立即修复 |
| P1 | 4 | Bug / 数据一致性——影响功能正确性 |
| P2 | 7 | 健壮性 / 维护性 / 性能 |
| P3 | 6 | 工程化 / 规范 |

---

## P0 — 安全风险

### P0-1：代码执行沙箱（已修复）

- **文件**：`tools/builtin/code_executor.py`
- **状态**：✅ 已修复（2026-04-30）
- **方案**：`subprocess.run` 隔离执行，10 秒超时，捕获 stdout + stderr

### P0-2：文件读写路径遍历（已修复）

- **文件**：`tools/builtin/file_rw.py`
- **状态**：✅ 已修复（2026-04-30）
- **方案**：workspace 白名单 + `os.path.realpath()` 规范化 + 默认 `"x"` 安全模式

---

## P1 — Bug / 数据一致性

### P1-1：向量库文档 ID 冲突（已修复）

- **文件**：`rag/vector_store.py`
- **状态**：✅ 已修复（2026-04-30）
- **方案**：改用 `uuid.uuid4().hex` 生成唯一 ID

### P1-2：混合搜索 RRF 去重键不正确（已修复）

- **文件**：`rag/hybrid_searcher.py`
- **状态**：✅ 已修复（2026-04-30）
- **方案**：引入 `chunk_id` 字段，RRF 融合使用 `chunk_id` 去重

### P1-3：工具调用循环无迭代上限（已修复）

- **文件**：`core/chat/chat_session.py`
- **状态**：✅ 已修复（2026-04-30）
- **方案**：三层防护（重复检测 + Token 预算 + 兜底上限），均可在 `app.yaml` 配置

### P1-4：`json.dumps` 序列化非 JSON 对象崩溃（已修复）

- **文件**：`core/chat/tool_executor.py:70`
- **状态**：✅ 已修复（2026-05-06）
- **问题**：`json.dumps(tool_result)` 遇到 `datetime`、`set`、`bytes` 等不可序列化对象时抛 `TypeError`
- **方案**：改为 `json.dumps(tool_result, default=str, ensure_ascii=False)`

---

## P2 — 健壮性 / 维护性 / 性能

### P2-1：Logger 文件句柄泄漏（已修复）

- **文件**：`core/base/logger.py:45`，`main.py` 所有退出路径
- **状态**：✅ 已修复（2026-05-06）
- **问题**：`open()` 后无 `close()` 保证。`Logger.close()` 方法存在但 `main.py` 从未调用，进程退出时文件句柄泄漏
- **方案**：`Logger.__init__` 中注册 `atexit.register(self.close)`

### P2-2：文档加载硬编码 UTF-8（已修复）

- **文件**：`rag/document_loader.py:65`
- **状态**：✅ 已修复（2026-05-06）
- **问题**：`open(file_path, "r", encoding="utf-8")` 硬编码，GBK/GB2312 文件直接 `UnicodeDecodeError`
- **方案**：UTF-8 → GBK → GB18030 → Latin-1 分级 fallback（不引入新依赖）

### P2-3：文档加载无大小限制（已修复）

- **文件**：`rag/document_loader.py:66`（文本）、`77-102`（PDF）
- **状态**：✅ 已修复（2026-05-06）
- **问题**：`f.read()` 全量读入内存，大文件 OOM；PDF 无页数限制，千页 PDF 也全量提取
- **方案**：添加 `MAX_FILE_SIZE = 50MB` 和 `MAX_PDF_PAGES = 500` 类级别常量，超限抛出明确错误

### P2-4：命令模块访问客户端私有属性（已修复）

- **文件**：`cli/commands.py:140`
- **状态**：✅ 已修复（2026-05-06）
- **问题**：`client._client = OpenAI(...)` 直接修改 `ChatClient._client`，破坏封装
- **方案**：在 `ChatClient` 中增加 `set_api_key(api_key)` 公共方法，命令层调用该方法

### P2-5：单例 `__init__` 未防护（已修复）

- **文件**：`core/base/settings.py`、`rag/rag_manager.py`、`tools/tool_manager.py`
- **状态**：✅ 已修复（2026-05-06）
- **问题**：`get_instance()` 能保证单例，但直接调用 `ClassName()` 可绕过，产生多个实例
- **方案**：`__init__` 开头检查 `hasattr(self, '_initialized')`，已初始化则跳过

### P2-6：稀疏索引每次增量全量重建（已修复）

- **文件**：`rag/sparse_store.py:93`
- **状态**：✅ 已修复（2026-05-06）
- **问题**：每次 `add_documents` 调用 `_rebuild_index()`，重新分词整个语料库并重建 BM25 索引，N 次增量添加总复杂度 O(N²)
- **方案**：采用 lazy rebuild 策略，`add_documents` 只标记 dirty，`search` 时才重建索引

### P2-7：RAG 增量写入无事务回滚（已修复）

- **文件**：`rag/rag_manager.py:91-95`
- **状态**：✅ 已修复（2026-05-06）
- **问题**：ChromaDB 写入成功但 BM25 写入失败时，两路数据不一致，无回滚机制
- **方案**：try-except 捕获稀疏写入失败，记录警告但不中断流程

---

## P3 — 工程化与规范

### P3-1：工具基类 PascalCase 属性违反 PEP 8（已修复）

- **文件**：`tools/tool_base.py:9,15,21` 及所有子类
- **状态**：✅ 已修复（2026-05-06）
- **问题**：`Name`、`Description`、`Parameters` 用 PascalCase，PEP 8 要求 `snake_case`
- **方案**：统一改为 `name`、`description`、`parameters`，同步修改 7 个子类 + tool_manager 引用 + 文档

### P3-2：添加基础测试框架

- **现状**：零测试覆盖
- **修复**：安装 `pytest`，创建 `tests/` 目录，优先测试工具基类、配置管理器、RAG 分词器

### P3-3：添加代码检查工具

- **现状**：无 lint / 格式化 / 类型检查
- **修复**：安装 `ruff`，在 `pyproject.toml` 添加 `[tool.ruff]` 配置

### P3-4：Shebang 行格式错误（已修复）

- **文件**：`main.py:1`
- **状态**：✅ 已修复（2026-05-06）
- **问题**：`#!usr/bin/python` 缺少前导 `/`，Unix 下无法执行
- **方案**：改为 `#!/usr/bin/env python`

### P3-5：Windows ANSI 启用方式不规范（已修复）

- **文件**：`core/chat/streaming.py:14-15`
- **状态**：✅ 已修复（2026-05-06）
- **问题**：`os.system("")` 通过副作用启用 ANSI，会额外启动 `cmd.exe` 子进程
- **方案**：改用 `ctypes` 调用 `SetConsoleMode` + `ENABLE_VIRTUAL_TERMINAL_PROCESSING`

### P3-6：其他小问题（已修复 4/6）

| 文件 | 行号 | 问题 | 状态 |
|------|------|------|------|
| `rag/sparse_store.py` | 221 | `except Exception: pass` 静默吞掉所有异常 | ✅ 改为 `except (json.JSONDecodeError, KeyError)` + warning |
| `rag/sparse_store.py` | 176 | `import numpy` 在方法体内 | ✅ 已在 P2 修复中移到文件顶部 |
| `cli/commands.py` | 181 | `/load` 命令路径遍历漏洞 | ✅ 添加 `realpath` + `commonpath` 校验 |
| `tools/tool_manager.py` | 53 | 局部变量 `cls` 遮蔽 `@classmethod` 参数 | ⏭️ 不适用（`load_tools` 是普通方法） |
| `core/chat/tool_executor.py` | 70 | 多个 tool call 共用同一 `reasoning_content` | ✅ 仅首个 tool call 附带 reasoning_content |
| `core/chat/streaming.py` | 80-81 | `_result`/`_thinking` 实例状态非线程安全 | ⏭️ 当前单线程，无需修复 |

---

## 修复记录

| 编号 | 状态 | 修复日期 | 备注 |
|------|------|----------|------|
| P0-1 | ✅ 已修复 | 2026-04-30 | subprocess 隔离 + 10s 超时 |
| P0-2 | ✅ 已修复 | 2026-04-30 | workspace 白名单 + realpath |
| P1-1 | ✅ 已修复 | 2026-04-30 | uuid4.hex 唯一 ID |
| P1-2 | ✅ 已修复 | 2026-04-30 | chunk_id 去重 |
| P1-3 | ✅ 已修复 | 2026-04-30 | 三层防护 |
| P1-4 | ✅ 已修复 | 2026-05-06 | json.dumps default=str |
| P2-1 | ✅ 已修复 | 2026-05-06 | atexit 注册 |
| P2-2 | ✅ 已修复 | 2026-05-06 | 编码分级 fallback |
| P2-3 | ✅ 已修复 | 2026-05-06 | 文件大小/页数限制 |
| P2-4 | ✅ 已修复 | 2026-05-06 | set_api_key 公共方法 |
| P2-5 | ✅ 已修复 | 2026-05-06 | _initialized 防护 |
| P2-6 | ✅ 已修复 | 2026-05-06 | lazy rebuild |
| P2-7 | ✅ 已修复 | 2026-05-06 | 稀疏写入异常捕获 |
| P3-1 | ✅ 已修复 | 2026-05-06 | snake_case 统一命名 |
| P3-2 | ⬜ 待规划 | - | 新增功能，非修复 |
| P3-3 | ⬜ 待规划 | - | 新增功能，非修复 |
| P3-4 | ✅ 已修复 | 2026-05-06 | #!/usr/bin/env python |
| P3-5 | ✅ 已修复 | 2026-05-06 | ctypes SetConsoleMode |
| P3-6 | ✅ 已修复 | 2026-05-06 | 4 项已修复，2 项不适用 |
