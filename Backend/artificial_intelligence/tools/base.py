from __future__ import annotations

from langchain_core.tools import BaseTool

from Backend.artificial_intelligence.config.config import AppConfig
from Backend.artificial_intelligence.tools.builtin import load_builtin_tools
from Backend.artificial_intelligence.tools.copywriting import load_copywriting_tools
from Backend.artificial_intelligence.tools.mcp import load_mcp_tools
from Backend.artificial_intelligence.tools.media.image_tools import load_image_tools
from Backend.artificial_intelligence.tools.media.video_tools import load_video_tools
from Backend.artificial_intelligence.tools.media.tts_tools import load_tts_tools
from Backend.artificial_intelligence.tools.media.music_tools import load_music_tools


def load_tools(config: AppConfig) -> list[BaseTool]:
    tools: list[BaseTool] = []
    tools.extend(load_builtin_tools())
    tools.extend(load_copywriting_tools(config))
    tools.extend(load_mcp_tools(config))
    tools.extend(load_image_tools(config))
    tools.extend(load_video_tools(config))
    tools.extend(load_tts_tools(config))
    tools.extend(load_music_tools(config))
    return tools


__all__ = ["load_tools"]
