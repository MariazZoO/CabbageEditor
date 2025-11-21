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


def wrap_tool_for_agent(tool_func: Callable[..., str]) -> Callable[..., str]:
    """
    包装工具函数，使其返回的 interface_type 统一为 "integrated"

    Args:
        tool_func: 原始工具函数（返回 JSON 字符串）

    Returns:
        包装后的函数（返回 interface_type="integrated" 的 JSON）
    """

    def wrapped(*args: Any, **kwargs: Any) -> str:
        # 调用原始工具
        result_json = tool_func(*args, **kwargs)

        try:
            # 解析 JSON
            result_dict = json.loads(result_json)

            # 修改 interface_type 为 "integrated"
            if "llm_content" in result_dict and isinstance(
                result_dict["llm_content"], list
            ):
                for content_item in result_dict["llm_content"]:
                    if isinstance(content_item, dict):
                        content_item["interface_type"] = "integrated"

            # 返回修改后的 JSON
            return json.dumps(result_dict, ensure_ascii=False)
        except (json.JSONDecodeError, KeyError, TypeError):
            # 如果解析失败，返回原始结果
            return result_json

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
