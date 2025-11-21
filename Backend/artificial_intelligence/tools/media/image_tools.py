from __future__ import annotations

from typing import List

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from Backend.artificial_intelligence.config.ai_config import AIConfig, MediaToolConfig
from Backend.artificial_intelligence.models.client_image import LingyaImageClient
from Backend.artificial_intelligence.tools.response_adapter import (
    build_part,
    build_success_result,
    build_error_result,
)

# from Backend.artificial_intelligence.storage import get_media_store


class ImageGenerationInput(BaseModel):
    """图片生成输入参数

    此类定义了 AI 图片生成功能所需的所有参数。
    支持纯文本生成和基于产品/场景图片的合成编辑。
    """

    prompt: str = Field(
        ...,
        description=(
            "图片生成提示词，用于描述要生成的图片内容。"
            "应详细描述图片的主题、风格、色调、构图、细节等元素。"
            "例如：'一个现代简约风格的客厅，米白色沙发，木质茶几，阳光从落地窗洒入，暖色调'。"
            "提示词越详细，生成的图片效果越符合预期。"
        ),
    )
    aspect_ratio: str = Field(
        default="1:1",
        description=(
            "图片比例设置（仅纯文本生成时有效，图生图时此参数无效）。"
            "支持的比例：1:1（正方形）, 16:9（横向）, 9:16（竖向）, 4:3, 3:4, 3:2, 2:3, 1:2。"
            "默认为 1:1。"
        ),
    )
    product_url: str | None = Field(
        default=None,
        description=(
            "可选：产品图片的 URL，用于图片合成或编辑场景。"
            "支持以下格式："
            "\n- http:// 或 https:// 网络图片 URL"
            "\n- data:image/...;base64,... 格式的 base64 数据 URI"
            "\n当提供此参数时，AI 会将产品融入到生成的场景中，此时 aspect_ratio 参数无效。"
        ),
    )
    scene_url: str | None = Field(
        default=None,
        description=(
            "可选：场景图片的 URL，用于图片合成或编辑场景。"
            "支持以下格式："
            "\n- http:// 或 https:// 网络图片 URL"
            "\n- data:image/...;base64,... 格式的 base64 数据 URI"
            "\n当提供此参数时，AI 会基于该场景进行图片生成或编辑，此时 aspect_ratio 参数无效。"
        ),
    )


def load_image_tools(config: AIConfig) -> List[StructuredTool]:
    image_cfg = config.media.image
    if not _is_media_tool_enabled(image_cfg, config):
        return []

    provider = config.providers[image_cfg.provider]
    client = LingyaImageClient(
        provider=provider,
        model=image_cfg.model,
        base_url=image_cfg.base_url,
    )
    # store = get_media_store()

    def _generate(
        prompt: str,
        aspect_ratio: str = "1:1",
        product_url: str | None = None,
        scene_url: str | None = None,
    ) -> str:
        data = ImageGenerationInput(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            product_url=product_url,
            scene_url=scene_url,
        )

        try:
            image_url, mime_type = client.generate(
                prompt=data.prompt,
                aspect_ratio=data.aspect_ratio,
                store=None,
                product_url=data.product_url,
                scene_url=data.scene_url,
            )

            # 构建 part
            part = build_part(
                content_type="image",
                content_text=data.prompt,
                content_url=image_url,
                parameter={
                    "resolution": data.aspect_ratio,
                    "text_type": "image_generation",
                },
            )

            # 返回成功结果
            return build_success_result(
                parts=[part],
                metadata={
                    "model": image_cfg.model,
                    "provider": provider.name,
                },
            ).to_envelope(interface_type="image")

        except Exception as e:
            return build_error_result(error_message=str(e)).to_envelope(
                interface_type="image"
            )

    tool = StructuredTool(
        name="generate_image",
        description=(
            "根据文本提示词生成图片，返回图片URL。支持三种模式："
            "\n1. 纯文本生成：提供 prompt 和 aspect_ratio（默认1:1）"
            "\n2. 图片编辑/合成：提供 prompt 和 product_url/scene_url（此时忽略aspect_ratio）"
            "\n支持的图片比例：1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3, 1:2"
        ),
        args_schema=ImageGenerationInput,
        func=_generate,
    )
    return [tool]


def _is_media_tool_enabled(cfg: MediaToolConfig, config: AIConfig) -> bool:
    if not cfg.enable:
        return False
    if not cfg.provider or not cfg.model:
        return False
    if cfg.provider not in config.providers:
        return False
    provider = config.providers[cfg.provider]
    return bool(provider.api_key and provider.base_url)


__all__ = ["load_image_tools"]
