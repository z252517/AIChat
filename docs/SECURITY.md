# 安全机制

## 代码执行沙箱

`tools/builtin/code_executor.py` — 在独立子进程中隔离执行 Python 代码。

### 设计

| 维度 | 实现 |
|------|------|
| 进程隔离 | `subprocess.run([sys.executable, "-I", "-c", code])` |
| 超时限制 | `timeout=10` 秒 |
| 输出捕获 | `capture_output=True` 同时捕获 stdout 和 stderr |
| 隔离标志 | `-I` 忽略用户 site-packages，减少侧信道 |

### 旧方案的问题（已修复）

- ~~字符串黑名单 `if "subprocess" in code`~~ → 极易绕过（`__import__`、字符串拼接）
- ~~`exec(code, {"__builtins__": __builtins__})`~~ → 暴露完整内置，可执行任意命令
- ~~无超时~~ → 无限循环挂起主进程
- ~~stderr 泄露到终端~~ → 错误信息被遗漏

---

## 文件操作沙箱

`tools/builtin/file_rw.py` — 所有读写操作限制在 workspace 白名单目录内。

### 路径校验流程

```
用户输入 file_path
  → 非绝对路径 → 拼接到 workspace 下
  → os.path.realpath() 规范化（解析 ../、符号链接）
  → os.path.commonpath(解析后, workspace) == workspace ?
     ├─ 是 → 放行
     └─ 否 → 拒绝，返回安全提示
```

### 写入模式

| 模式 | 行为 | 使用场景 |
|------|------|----------|
| `"x"` | 仅当文件不存在时创建（**默认**） | 新建文件 |
| `"w"` | 覆盖写入（需显式指定） | 显式覆盖 |
| `"a"` | 追加写入 | 日志场景 |

### 配置

```yaml
# config/app.yaml
workspace:
  dir: "workspace"   # 相对于 ~/.ai-chat-cli/，启动时自动创建
```

---

## 工具调用循环防护

`core/chat/chat_session.py` 的 `chat()` 方法在 `finish_reason == "tool_calls"` 循环中设置三层防护：

### 退出路径

```
┌──────────────────────────────────────────────────┐
│ 正常退出（99% 场景）                              │
│ finish_reason != "tool_calls" → 模型产出文本回复  │
├──────────────────────────────────────────────────┤
│ 防护层 1: 重复检测 ← 最早触发                     │
│ 连续 N 轮相同工具 + 相同参数 → 终止               │
├──────────────────────────────────────────────────┤
│ 防护层 2: Token 预算                              │
│ 累计 token 超限 → 终止并提示拆分任务              │
├──────────────────────────────────────────────────┤
│ 防护层 3: 兜底上限 ← 安全网                       │
│ 轮次超过上限 → 终止（前两层失效时生效）            │
└──────────────────────────────────────────────────┘
```

### 配置

```yaml
# config/app.yaml
tool:
  max_rounds: 20            # 兜底上限
  stale_rounds: 3           # 连续相同调用视为死循环
  max_tool_tokens: 100000   # 累计 Token 预算
```

### 重复检测实现

每轮工具调用后生成签名 `tuple((name, arguments), ...)`，与上一轮签名比对。相同签名计数递增，不同则重置。达到 `stale_rounds` 阈值时终止循环。
