from __future__ import annotations

import json
from typing import Any, Callable

from langchain_core.tools import BaseTool, StructuredTool

from Backend.artificial_intelligence.config.ai_config import AIConfig
from Backend.artificial_intelligence.tools.test_tools import load_test_tools
from Backend.artificial_intelligence.tools.text import load_text_tools
from Backend.artificial_intelligence.tools.mcp import load_mcp_tools
from Backend.artificial_intelligence.tools.media.image_tools import load_image_tools
from Backend.artificial_intelligence.tools.media.video_tools import load_video_tools
from Backend.artificial_intelligence.tools.media.speech_tools import load_speech_tools
from Backend.artificial_intelligence.tools.media.music_tools import load_music_tools


def load_tools(config: AIConfig) -> list[BaseTool]:
    tools: list[BaseTool] = []
    tools.extend(load_test_tools())
    tools.extend(load_text_tools(config))
    tools.extend(load_mcp_tools(config))
    tools.extend(load_image_tools(config))
    tools.extend(load_video_tools(config))
    tools.extend(load_speech_tools(config))
    tools.extend(load_music_tools(config))
    return tools


def wrap_tool_for_agent(tool_func: Callable[..., str | dict]) -> Callable[..., str]:
    """
    包装工具函数，使其返回的 interface_type 统一为 "integrated"

    Args:
        tool_func: 原始工具函数（返回 JSON 字符串或字典）

    Returns:
        包装后的函数（返回 interface_type="integrated" 的 JSON 字符串）
    """

    def wrapped(*args: Any, **kwargs: Any) -> str:
        from Backend.artificial_intelligence.tools.response_adapter import tool_context

        # 使用 Context 注入 interface_type
        # Context 优先级高于工具内部参数，因此无需后续解析修改
        with tool_context(interface_type="integrated"):
            result = tool_func(*args, **kwargs)

        # 情况 1: 工具返回字典 (新模式 - 推荐)
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False)

        # 情况 2: 工具返回字符串 (旧模式 - 兼容)
        # 由于 Context 已经注入，如果工具使用了 response_adapter，
        # 它生成的 JSON 应该已经包含了 interface_type="integrated"。
        # 所以这里直接返回即可，无需解析。
        return result

    # 保留原函数的元数据（用于 LangChain 工具识别）
    wrapped.__name__ = tool_func.__name__
    wrapped.__doc__ = tool_func.__doc__
    if hasattr(tool_func, "__annotations__"):
        wrapped.__annotations__ = tool_func.__annotations__

    return wrapped


def wrap_tools_for_agent(tools: list) -> list:
    """
    批量包装工具列表供 Agent 使用

    Args:
        tools: LangChain 工具列表（StructuredTool 等）

    Returns:
        包装后的工具列表（interface_type 将被改为 "integrated"）
    """
    wrapped_tools = []
    for tool in tools:
        if isinstance(tool, StructuredTool):
            # 包装 StructuredTool 的 func
            wrapped_func = wrap_tool_for_agent(tool.func)
            wrapped_tool = StructuredTool(
                name=tool.name,
                description=tool.description,
                func=wrapped_func,
                args_schema=tool.args_schema,
            )
            wrapped_tools.append(wrapped_tool)
        else:
            # 其他类型工具尝试包装
            if hasattr(tool, "func"):
                tool.func = wrap_tool_for_agent(tool.func)
            wrapped_tools.append(tool)

    return wrapped_tools


__all__ = ["load_tools", "wrap_tool_for_agent", "wrap_tools_for_agent"]
