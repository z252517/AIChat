# -*- coding: utf-8 -*-

"""
终端显示模块
统一管理所有终端输出的格式和样式，其他模块通过此模块输出
"""

import os


class Display:
    """终端显示器，统一管理所有终端输出"""

    # ============ 样式常量 ============

    SEPARATOR = "=" * 50

    # ANSI 颜色 / 样式
    _BOLD = "\033[1m"
    _DIM = "\033[2m"
    _CYAN = "\033[36m"
    _GREEN = "\033[32m"
    _YELLOW = "\033[33m"
    _RED = "\033[31m"
    _MAGENTA = "\033[35m"
    _BLUE = "\033[34m"
    _GRAY = "\033[90m"
    _WHITE = "\033[97m"
    _RESET = "\033[0m"

    # ============ 通用输出 ============

    def banner(self, title):
        """打印横幅标题"""
        print(f"{self._CYAN}{self.SEPARATOR}")
        print(f"  {title}")
        print(f"{self.SEPARATOR}{self._RESET}")

    def info(self, message):
        """打印信息提示 [xxx]"""
        print(f"{self._BLUE}[{message}]{self._RESET}")

    def error(self, message):
        """打印错误信息"""
        print(f"\n{self._RED}[请求出错: {message}]{self._RESET}")

    def newline(self):
        """打印空行"""
        print()

    # ============ 对话输出 ============

    def user_prompt(self):
        """显示用户输入提示，返回用户输入"""
        print()
        try:
            return input(f"{self._GREEN}{self._BOLD}你: {self._RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！👋")
            return None

    def ai_prefix(self):
        """打印 AI 回复前缀"""
        print(f"\n{self._CYAN}{self._BOLD}AI: {self._RESET}", end="")

    def ai_text(self, text):
        """流式输出 AI 文本内容"""
        print(text, end="", flush=True)

    def ai_end(self):
        """AI 回复结束"""
        print()

    # ============ 思考过程输出 ============

    def thinking_start(self):
        """打印思考开始"""
        print(f"\n{self._GRAY}{'─' * 15} 💭 思考中 {'─' * 15}")

    def thinking_text(self, text):
        """流式输出思考内容（灰色由 thinking_start 开启，此处直接输出）"""
        print(text, end="", flush=True)

    def thinking_end(self):
        """打印思考结束"""
        print(f"\n{'─' * 15} 思考结束 {'─' * 15}{self._RESET}")

    # ============ 工具调用输出 ============

    def tool_call_start(self):
        """打印工具调用开始"""
        print(f"\n{self._YELLOW}{'─' * 15} 🔧 调用工具 {'─' * 15}")

    def tool_call_info(self, name, arguments, call_id):
        """打印单个工具调用信息"""
        print(f"  工具: {self._BOLD}{name}{self._RESET}{self._YELLOW}, 参数: {arguments}, ID: {call_id}")

    def tool_executing(self, name):
        """打印工具执行中"""
        print(f"  ▶ 执行 {self._BOLD}{name}{self._RESET}{self._YELLOW} ...", end="", flush=True)

    def tool_result(self, result_preview):
        """打印工具执行结果（接在 tool_executing 同一行后面）"""
        print(f" ✅ 完成 ({len(result_preview)} 字符)")

    def tool_call_end(self):
        """打印工具调用结束"""
        print(f"{'─' * 15} 工具调用结束 {'─' * 14}{self._RESET}")

    # ============ 引导输出 ============

    def show_selection(self, title, options):
        """
        显示编号选择列表

        Args:
            title: 标题
            options: 选项列表 [(display_text, value), ...]
        """
        print(f"\n{self._BLUE}{title}{self._RESET}")
        for i, (text, _) in enumerate(options, 1):
            print(f"  {self._CYAN}{i}.{self._RESET} {text}")

    def input_prompt(self, prompt):
        """
        显示输入提示，返回用户输入

        Args:
            prompt: 提示文字

        Returns:
            str: 用户输入内容，Ctrl+C 返回 None
        """
        try:
            return input(f"{self._GREEN}{prompt}{self._RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return None

    # ============ 命令反馈输出 ============

    def goodbye(self):
        """打印再见"""
        print("再见！👋")

    def show_history(self, messages):
        """显示对话历史（tool 相关消息只显示简要信息）"""
        print(f"{self._BLUE}[当前对话历史: {len(messages)} 条消息]{self._RESET}")
        for i, msg in enumerate(messages):
            role = msg.get("role", "?")
            content = msg.get("content", "")

            # assistant 带 tool_calls：只显示调用了哪些工具
            if role == "assistant" and msg.get("tool_calls"):
                names = [tc["function"]["name"] for tc in msg["tool_calls"]]
                print(f"  {self._GRAY}[{i}] assistant: 🔧 调用工具 → {', '.join(names)}{self._RESET}")
                continue

            # tool 返回结果：只显示工具名和结果长度
            if role == "tool":
                call_id = msg.get("tool_call_id", "?")
                length = len(content)
                print(f"  {self._GRAY}[{i}] tool: 返回结果 ({length} 字符) [id={call_id}]{self._RESET}")
                continue

            # 其他消息正常预览
            preview = (content[:80] + "...") if len(content) > 80 else content
            print(f"  {self._GRAY}[{i}] {role}: {preview}{self._RESET}")

    def show_files(self, files, get_basename):
        """显示可用的历史文件列表"""
        if files:
            print(f"{self._BLUE}[可用的历史文件:]{self._RESET}")
            for i, f in enumerate(files, 1):
                print(f"  {i}. {get_basename(f)}")
            print(f"用法: /load <文件名>")
        else:
            print(f"{self._YELLOW}[没有已保存的历史文件]{self._RESET}")

    def show_rag_topic_stats(self, topic, stats):
        """显示单个 RAG 主题的状态"""
        print(f"{self._BLUE}[知识库主题 '{topic}' 状态:]{self._RESET}")
        print(f"  文档片段数: {stats['total_chunks']}")
        sources = ', '.join(stats['sources']) if stats['sources'] else '无'
        print(f"  文件来源: {sources}")

    def show_rag_global_stats(self, stats):
        """显示 RAG 全局状态"""
        print(f"{self._BLUE}[知识库全局状态:]{self._RESET}")
        print(f"  主题数: {stats.get('topic_count', 0)}")
        print(f"  总片段数: {stats['total_chunks']}")
        print(f"  总文件数: {stats['source_count']}")
        if stats.get("topics"):
            for t, t_stats in stats["topics"].items():
                sources = ', '.join(t_stats['sources'])
                print(f"  {self._GRAY}[{t}]{self._RESET} {t_stats['total_chunks']} 片段, 文件: {sources}")

    def show_rag_topics(self, topic_list):
        """显示 RAG 主题列表，topic_list: [(name, chunks, file_count), ...]"""
        if topic_list:
            print(f"{self._BLUE}[知识库主题列表 ({len(topic_list)} 个):]{self._RESET}")
            for name, chunks, file_count in topic_list:
                print(f"  • {name} — {chunks} 片段, {file_count} 个文件")
        else:
            print(f"{self._YELLOW}[知识库为空，暂无主题]{self._RESET}")

    def show_rag_help(self):
        """显示 RAG 子命令帮助"""
        print(f"{self._BLUE}[RAG 知识库命令:]{self._RESET}")
        print(f"  {self._CYAN}/rag status [主题]{self._RESET}       - 查看知识库状态")
        print(f"  {self._CYAN}/rag add <文件路径> [主题]{self._RESET} - 添加文件到知识库")
        print(f"  {self._CYAN}/rag topics{self._RESET}              - 列出所有主题")
        print(f"  {self._CYAN}/rag clear [主题]{self._RESET}         - 清空知识库（可指定主题）")

    def show_help(self):
        """显示帮助信息"""
        print(f"{self._BLUE}[可用命令:]{self._RESET}")
        print(f"  {self._CYAN}/setkey <Key>{self._RESET}    - 设置 API Key（持久保存）")
        print(f"  {self._CYAN}/setmodel{self._RESET}        - 查看/切换模型（持久保存）")
        print(f"  {self._CYAN}/exit{self._RESET}            - 退出程序")
        print(f"  {self._CYAN}/clear{self._RESET}           - 清空对话历史")
        print(f"  {self._CYAN}/history{self._RESET}         - 查看对话历史")
        print(f"  {self._CYAN}/save{self._RESET}            - 保存对话历史")
        print(f"  {self._CYAN}/load{self._RESET}            - 列出所有已保存的历史文件")
        print(f"  {self._CYAN}/load <文件名>{self._RESET}   - 加载指定历史文件")
        print(f"  {self._CYAN}/tokens{self._RESET}          - 查看 Token 用量")
        print(f"  {self._CYAN}/rag{self._RESET}             - RAG 知识库管理（status/add/topics/clear）")
        print(f"  {self._CYAN}/help{self._RESET}            - 显示此帮助")
