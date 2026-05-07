from datetime import datetime, timezone, timedelta
from ai_chat_cli.tools.tool_base import ToolBase


class GetCurrentTime(ToolBase):
    """获取当前时间的工具（含时区信息）"""

    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return (
            "获取现在的真实日期和时间。"
            "当用户询问今天几号、现在几点、当前时间、当前日期、星期几、几月几日、"
            "什么时候、年份、几点了等任何与时间日期相关的问题时，必须调用此工具获取准确信息。"
            "返回格式: YYYY-MM-DD HH:MM:SS UTC+offset"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def execute(self, **kwargs):
        local_now = datetime.now().astimezone()
        utc_offset = local_now.utcoffset()
        total_seconds = int(utc_offset.total_seconds())
        hours, remainder = divmod(abs(total_seconds), 3600)
        minutes = remainder // 60
        sign = "+" if total_seconds >= 0 else "-"
        if minutes:
            tz_str = f"UTC{sign}{hours}:{minutes:02d}"
        else:
            tz_str = f"UTC{sign}{hours}"
        return f"{local_now.strftime('%Y-%m-%d %H:%M:%S')} {tz_str}"
