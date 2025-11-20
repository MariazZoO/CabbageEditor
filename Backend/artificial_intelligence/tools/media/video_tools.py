"""
视频生成工具
提供基于 LangChain 的视频生成功能（图生视频）
"""

from __future__ import annotations

import json
from typing import List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from Backend.artificial_intelligence.config.ai_config import AIConfig, MediaToolConfig
from Backend.artificial_intelligence.models.client_video import DashScopeVideoClient
from Backend.artificial_intelligence.models.video_utils import resolve_image_url
# from Backend.artificial_intelligence.storage import get_media_store


class VideoGenerationInput(BaseModel):
    """视频生成输入参数

    此类定义了图生视频功能所需的所有参数。
    支持基于单张图片和文本提示词生成动态视频内容。
    """

    prompt: str = Field(
        ...,
        description=(
            "视频生成提示词，用于描述要生成的视频内容。"
            "应详细描述视频中的动作、场景、运动方式、氛围等元素。"
            "例如：'镜头缓慢推进，树叶在微风中轻轻摇曳，阳光透过枝叶洒下斑驳光影'。"
            "提示词越详细，生成的视频效果越精确。"
        ),
    )
    image_url: str = Field(
        ...,
        description=(
            "输入图片的 URL，作为视频生成的起始帧。支持以下格式："
            "\n1) data:image/...;base64,... - Base64 编码的图片数据 URI（推荐）；"
            "\n2) http:// 或 https:// - 网络图片 URL；"
            "\n3) file:// - 本地文件路径（需要是绝对路径）。"
            "\n注意：图片会被解析并转换为模型可接受的格式，如果图片无法加载将返回错误。"
        ),
    )
    resolution: str = Field(
        default="720P",
        description=(
            "视频输出分辨率，影响视频清晰度和文件大小。"
            "支持三种规格："
            "\n- '480P'：标清，文件较小，生成速度较快；"
            "\n- '720P'：高清，平衡质量与性能（默认推荐）；"
            "\n- '1080P'：全高清，最佳画质但文件较大，生成时间较长。"
            "\n注意：必须使用准确的字符串值（区分大小写），否则会返回参数错误。"
        ),
    )
    prompt_extend: bool = Field(
        default=True,
        description=(
            "是否启用提示词智能扩展功能。"
            "当设置为 True 时，模型会自动优化和扩展用户的提示词，补充更多细节以提升生成质量。"
            "扩展后的提示词会在返回结果的 'actual_prompt' 字段中体现，"
            "原始提示词会保留在 'orig_prompt' 字段中。"
            "建议保持默认开启以获得更好的视频效果。"
        ),
    )


def load_video_tools(config: AIConfig) -> List[StructuredTool]:
    """
    加载视频生成工具

    参数:
    - config: 应用配置

    返回:
    - LangChain StructuredTool 列表
    """
    video_cfg = config.media.video
    if not _is_media_tool_enabled(video_cfg, config):
        return []

    provider = config.providers[video_cfg.provider]
    client = DashScopeVideoClient(
        provider=provider,
        model=video_cfg.model or "wan2.2-i2v-flash",
        base_url=video_cfg.base_url,
    )
    # media_store = get_media_store()

    def _generate_video(
        prompt: str,
        image_url: str,
        resolution: str = "720P",
        prompt_extend: bool = True,
    ) -> str:
        """图生视频：根据图片和提示词生成视频。"""
        data = VideoGenerationInput(
            prompt=prompt,
            image_url=image_url,
            resolution=resolution,
            prompt_extend=prompt_extend,
        )

        # 验证分辨率参数
        valid_resolutions = {"480P", "720P", "1080P"}
        if data.resolution not in valid_resolutions:
            return json.dumps(
                {
                    "type": "video_generation",
                    "status": "failed",
                    "error": f"无效的分辨率: {data.resolution}，支持的值: {', '.join(valid_resolutions)}",
                },
                ensure_ascii=False,
            )

        # 准备图片 URL
        image_url = resolve_image_url(data.image_url, None)
        if not image_url:
            return json.dumps(
                {
                    "type": "video_generation",
                    "status": "failed",
                    "error": f"无法加载图片：{data.image_url}",
                },
                ensure_ascii=False,
            )

        # 生成视频
        try:
            result = client.generate_video_from_image(
                prompt=data.prompt,
                image_url=image_url,
                resolution=data.resolution,
                prompt_extend=data.prompt_extend,
                max_wait_seconds=600,
                poll_interval=5.0,
            )

            # 构建响应数据
            payload = {
                "type": "video_generation",
                "status": "succeeded",
                "prompt": data.prompt,
                "source": provider.name,
                "model": client.model,
                "video_url": result.get("output", {}).get("video_url"),
                "task_id": result.get("task_id"),
                "resolution": data.resolution,
            }

            # 添加可选字段
            output = result.get("output", {})
            if "orig_prompt" in output:
                payload["orig_prompt"] = output["orig_prompt"]
            if "actual_prompt" in output:
                payload["actual_prompt"] = output["actual_prompt"]
            if "usage" in result:
                payload["usage"] = result["usage"]

            return json.dumps(payload, ensure_ascii=False)

        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"视频生成失败: {e}", exc_info=True
            )
            return json.dumps(
                {
                    "type": "video_generation",
                    "status": "failed",
                    "error": str(e),
                },
                ensure_ascii=False,
            )

    tool = StructuredTool(
        name="generate_video_from_image",
        description=(
            "根据图片和文本提示词生成视频（图生视频），返回云端视频 URL。"
            "输入需要包含："
            "1) 视频生成提示词（描述动作、场景、运动等）；"
            "2) 输入图片的 URL（支持 base64 data URI、HTTP(S) URL 或 file:// URL）。"
            "可选参数包括分辨率（480P/720P/1080P，默认720P）和提示词扩展开关（默认开启）。"
        ),
        args_schema=VideoGenerationInput,
        func=_generate_video,
    )

    return [tool]


def _is_media_tool_enabled(cfg: MediaToolConfig, config: AIConfig) -> bool:
    """检查媒体工具是否启用"""
    if not cfg.enable:
        return False
    if not cfg.provider or not cfg.model:
        return False
    if cfg.provider not in config.providers:
        return False
    provider = config.providers[cfg.provider]
    return bool(provider.api_key)


__all__ = ["load_video_tools"]
