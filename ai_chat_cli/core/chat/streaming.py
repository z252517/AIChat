# -*- coding: utf-8 -*-

"""
流式响应处理器
负责解析 OpenAI 流式输出中的思考内容、文本内容和 tool_calls 数据
"""

import os
import time
import queue
import threading


def _enable_windows_ansi_support():
    """Windows 终端启用 ANSI 转义码支持（非关键功能，失败时静默降级）"""
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        handle = kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        if handle == -1:  # INVALID_HANDLE_VALUE
            return
        mode = ctypes.c_ulong()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception:
        pass


_ansi_initialized = False


def _ensure_ansi_support():
    """惰性初始化 Windows ANSI 支持（首次使用时执行）"""
    global _ansi_initialized
    if _ansi_initialized:
        return
    _ansi_initialized = True
    _enable_windows_ansi_support()


class _StreamResult:
    """流式处理的结果（内部类）"""

    def __init__(self):
        self.content = ""               # 模型回复的文本内容
        self.reasoning_content = ""      # 模型的思考内容
        self.tool_calls_map = {}         # {index: {"id", "name", "arguments"}}
        self.finish_reason = None        # "stop", "tool_calls", etc.
        self.usage = None                # {"prompt_tokens", "completion_tokens", "total_tokens"}


class _Spinner:
    """等待动画（内部类），等待响应时显示旋转动画和已等待时间"""

    _FRAMES = ["|", "/", "-", "\\"]

    def __init__(self, message="AI 思考中"):
        self._message = message
        self._running = False
        self._thread = None
        self._start_time = None

    def start(self):
        self._running = True
        self._start_time = time.time()
        self._thread = threading.Thread(target=self._animate, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        print("\r" + " " * 60 + "\r", end="", flush=True)

    def _animate(self):
        idx = 0
        while self._running:
            elapsed = time.time() - self._start_time
            frame = self._FRAMES[idx % len(self._FRAMES)]
            print(f"\r{frame} {self._message}... ({elapsed:.1f}s)", end="", flush=True)
            idx += 1
            time.sleep(0.1)


class StreamHandler:
    """
    流式响应处理器
    网络请求在后台线程执行，主线程负责等待动画和数据解析
    """

    def process(self, request_func):
        """
        处理流式响应，收集并返回完整结果

        Args:
            request_func: 无参可调用对象，返回 OpenAI 流式响应

        Returns:
            _StreamResult: 完整的回复内容、思考内容、tool_calls 和结束原因
        """
        _ensure_ansi_support()
        from ai_chat_cli.core.base.services import Service, ServiceKey
        self._display = Service.get(ServiceKey.DISPLAY)
        self._result = _StreamResult()
        self._thinking = False

        chunk_queue = queue.Queue()
        reader = self._start_reader(request_func, chunk_queue)

        spinner = _Spinner()
        spinner.start()
        spinner_active = True

        try:
            spinner_active = self._consume_chunks(chunk_queue, spinner, spinner_active)
        finally:
            reader.join()
            if spinner_active:
                spinner.stop()

        return self._result

    # ==================== 内部：线程管理 ====================

    @staticmethod
    def _start_reader(request_func, chunk_queue):
        """启动后台线程：发起请求并将 chunk 逐个放入队列"""

        def _read():
            try:
                stream = request_func()
                for chunk in stream:
                    chunk_queue.put(chunk)
            except Exception as e:
                chunk_queue.put(e)
            finally:
                chunk_queue.put(None)  # 结束标记

        thread = threading.Thread(target=_read, daemon=True)
        thread.start()
        return thread

    # ==================== 内部：主循环 ====================

    def _consume_chunks(self, chunk_queue, spinner, spinner_active):
        """主线程轮询队列，处理每个 chunk"""
        while True:
            try:
                chunk = chunk_queue.get(timeout=0.05)
            except queue.Empty:
                continue

            if chunk is None:
                break

            if isinstance(chunk, Exception):
                if spinner_active:
                    spinner.stop()
                raise chunk

            # 提取 usage（API 在最后一个 chunk 返回）
            self._extract_usage(chunk)

            if not chunk.choices:
                continue

            choice = chunk.choices[0]

            # 首个有效数据到达时停止动画
            if spinner_active and self._has_data(choice.delta):
                spinner.stop()
                spinner_active = False

            # 解析 delta 内容
            self._process_delta(choice.delta)

            # 处理结束信号
            if choice.finish_reason:
                self._handle_finish(choice.finish_reason)

        return spinner_active

    # ==================== 内部：数据解析 ====================

    def _extract_usage(self, chunk):
        """提取 Token 用量信息"""
        if hasattr(chunk, "usage") and chunk.usage:
            self._result.usage = {
                "prompt_tokens": getattr(chunk.usage, "prompt_tokens", 0),
                "completion_tokens": getattr(chunk.usage, "completion_tokens", 0),
                "total_tokens": getattr(chunk.usage, "total_tokens", 0),
            }

    @staticmethod
    def _has_data(delta):
        """判断 delta 是否包含有效数据（用于停止等待动画）"""
        if not delta:
            return False
        return (
            (hasattr(delta, "reasoning_content") and getattr(delta, "reasoning_content"))
            or delta.content
            or delta.tool_calls
        )

    def _process_delta(self, delta):
        """分发处理 delta 中的各类内容"""
        if not delta:
            return
        self._process_reasoning(delta)
        self._process_content(delta)
        self._process_tool_calls(delta)

    def _process_reasoning(self, delta):
        """处理思考内容"""
        if not hasattr(delta, "reasoning_content"):
            return
        reasoning = getattr(delta, "reasoning_content")
        if not reasoning:
            return
        if not self._thinking:
            self._thinking = True
            self._display.thinking_start()
        self._result.reasoning_content += reasoning
        self._display.thinking_text(reasoning)

    def _process_content(self, delta):
        """处理普通文本内容"""
        if not delta.content:
            return
        if self._thinking:
            self._thinking = False
            self._display.thinking_end()
            self._display.newline()
        self._result.content += delta.content
        self._display.ai_text(delta.content)

    def _process_tool_calls(self, delta):
        """处理工具调用（流式中分散在多个 chunk）"""
        if not delta.tool_calls:
            return
        for tc in delta.tool_calls:
            idx = tc.index
            if idx not in self._result.tool_calls_map:
                self._result.tool_calls_map[idx] = {"id": "", "name": "", "arguments": ""}
            entry = self._result.tool_calls_map[idx]
            if tc.id:
                entry["id"] = tc.id
            if tc.function and tc.function.name:
                entry["name"] = tc.function.name
            if tc.function and tc.function.arguments:
                entry["arguments"] += tc.function.arguments

    def _handle_finish(self, finish_reason):
        """处理流结束信号"""
        self._result.finish_reason = finish_reason

        # 思考状态收尾
        if self._thinking:
            self._thinking = False
            self._display.thinking_end()

        # 工具调用时输出调用信息
        if finish_reason == "tool_calls":
            self._display.tool_call_start()
            for idx in sorted(self._result.tool_calls_map.keys()):
                tc = self._result.tool_calls_map[idx]
                self._display.tool_call_info(tc["name"], tc["arguments"], tc["id"])