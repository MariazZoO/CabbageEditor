"""
文案生成工具 - 使用豆包 LLM 专职生成各类文案内容
"""

from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage

from Backend.artificial_intelligence.config.ai_config import AIConfig
from Backend.artificial_intelligence.models import get_chat_model
from Backend.artificial_intelligence.tools.response_adapter import (
    build_part,
    build_success_result,
    build_error_result,
)


# 定义参数模式
class ProductTextInput(BaseModel):
    """产品文案生成的输入参数"""

    instruction: str = Field(..., description="产品描述及要求")
    style: str = Field(
        default="专业", description="文案风格，可选：专业、活泼、高端、亲切、幽默"
    )
    length: str = Field(default="中等", description="文案长度，可选：简短、中等、详细")


class MarketingTextInput(BaseModel):
    """营销文案生成的输入参数"""

    instruction: str = Field(..., description="营销活动描述及要求")
    platform: str = Field(
        default="通用", description="投放平台，可选：通用、微信、微博、抖音、小红书"
    )
    tone: str = Field(
        default="激励", description="文案语气，可选：激励、温暖、紧迫、趣味"
    )


class CreativeTextInput(BaseModel):
    """创意文案生成的输入参数"""

    instruction: str = Field(..., description="创作主题及要求")
    style: str = Field(
        default="现代", description="创作风格，可选：现代、古典、浪漫、科技、悬疑等"
    )
    length: str = Field(default="中等", description="作品长度，可选：简短、中等、长篇")


def load_text_tools(config: AIConfig) -> List[StructuredTool]:
    """
    加载文案生成工具

    该工具使用豆包LLM专门生成各类文案，包括：
    - 产品文案：产品描述、卖点提炼、广告语等
    - 营销文案：活动宣传、社交媒体文案等
    - 创意文案：故事、剧本、诗歌等
    """

    # 检查是否配置了豆包 provider
    if "doubao" not in config.providers:
        print("[警告] 未配置豆包provider，文案生成工具将不可用")
        return []

    # 使用豆包模型创建LLM实例
    # 豆包推荐使用 doubao-pro-32k 或 doubao-lite-32k 等模型
    llm = get_chat_model(
        config,
        provider_name="doubao",
        model_name="doubao-1-5-pro-32k-250115",  # 默认使用pro版本，更好的文案质量
        temperature=0.8,  # 较高的温度以增加创意性
        request_timeout=60.0,
    )

    def _generate_product_text(
        instruction: str,
        style: str = "专业",
        length: str = "中等",
    ) -> str:
        """
        生成产品文案

        Args:
            instruction: 产品描述及要求
            style: 文案风格（可选：专业、活泼、高端、亲切、幽默）
            length: 文案长度（可选：简短、中等、详细）

        Returns:
            生成的产品文案
        """
        length_map = {
            "简短": "50-80字",
            "中等": "150-200字",
            "详细": "300-500字",
        }

        prompt = f"""
请根据以下产品描述和要求，生成{style}风格的文案，长度约{length_map.get(length, '150-200字')}：

需求描述：{instruction}

要求：
1. 突出产品的核心卖点
2. 语言{style}且吸引人
3. 适合用于产品宣传和推广
4. 直接输出文案内容，不要输出任何解释
"""

        messages = [
            SystemMessage(
                content="你是一位专业的文案撰写专家，擅长创作各类营销文案、产品文案和创意内容。"
            ),
            HumanMessage(content=prompt),
        ]

        try:
            response = llm.invoke(messages)

            # 构建 part
            part = build_part(
                content_type="text",
                content_text=response.content,
                parameter={
                    "text_type": "product_text",
                },
            )

            # 返回成功结果
            return build_success_result(
                parts=[part],
            ).to_envelope(interface_type="text")
        except Exception as e:
            return build_error_result(error_message=str(e)).to_envelope(
                interface_type="text"
            )

    def _generate_marketing_text(
        instruction: str,
        platform: str = "通用",
        tone: str = "激励",
    ) -> str:
        """
        生成营销文案

        Args:
            instruction: 营销活动描述及要求
            platform: 投放平台（可选：通用、微信、微博、抖音、小红书）
            tone: 文案语气（可选：激励、温暖、紧迫、趣味）

        Returns:
            生成的营销文案
        """
        platform_tips = {
            "微信": "适合长文，可以加入emoji表情",
            "微博": "140字内，简洁有力",
            "抖音": "口语化，有节奏感",
            "小红书": "种草型，真实分享感",
            "通用": "适中长度，普适性强",
        }

        prompt = f"""
请根据以下营销活动描述，生成{tone}语气的文案：

需求描述：{instruction}
投放平台：{platform}

平台建议：{platform_tips.get(platform, platform_tips['通用'])}

要求：
1. 符合目标受众的语言习惯
2. 突出营销要点和优惠信息
3. 语气{tone}，能够引发行动
4. 直接输出文案内容，不要输出任何解释
"""

        messages = [
            SystemMessage(
                content="你是一位专业的营销文案专家，精通各类平台的文案创作和用户心理。"
            ),
            HumanMessage(content=prompt),
        ]

        try:
            response = llm.invoke(messages)

            # 构建 part
            part = build_part(
                content_type="text",
                content_text=response.content,
                parameter={
                    "text_type": "marketing_text",
                },
            )

            # 返回成功结果
            return build_success_result(
                parts=[part],
            ).to_envelope(interface_type="text")
        except Exception as e:
            return build_error_result(error_message=str(e)).to_envelope(
                interface_type="text"
            )

    def _generate_creative_text(
        instruction: str,
        style: str = "现代",
        length: str = "中等",
    ) -> str:
        """
        生成创意文案

        Args:
            instruction: 创作主题及要求
            style: 创作风格（可选：现代、古典、浪漫、科技、悬疑等）
            length: 作品长度（可选：简短、中等、长篇）

        Returns:
            生成的创意文案
        """
        length_map = {
            "简短": "100字以内",
            "中等": "300-500字",
            "长篇": "800-1000字",
        }

        prompt = f"""
请根据以下主题和要求，创作一个{style}风格的作品：

需求描述：{instruction}
作品长度：{length_map.get(length, '300-500字')}

要求：
1. 创意新颖，富有想象力
2. 风格符合{style}特点
3. 内容完整，结构合理
4. 直接输出作品内容，不要输出任何解释
"""

        messages = [
            SystemMessage(
                content="你是一位富有创意的文案创作者，擅长各种文学体裁和创意表达。"
            ),
            HumanMessage(content=prompt),
        ]

        try:
            response = llm.invoke(messages)

            # 构建 part
            part = build_part(
                content_type="text",
                content_text=response.content,
                parameter={
                    "text_type": "creative_text",
                },
            )

            # 返回成功结果
            return build_success_result(
                parts=[part],
            ).to_envelope(interface_type="text")
        except Exception as e:
            return build_error_result(error_message=str(e)).to_envelope(
                interface_type="text"
            )

    # 创建三个结构化工具，带有明确的参数模式
    tools = [
        StructuredTool(
            name="generate_product_text",
            description="生成产品文案，包括产品描述、卖点提炼、广告语等",
            func=_generate_product_text,
            args_schema=ProductTextInput,  # 添加参数模式
        ),
        StructuredTool(
            name="generate_marketing_text",
            description="生成营销文案，包括活动宣传、社交媒体文案等",
            func=_generate_marketing_text,
            args_schema=MarketingTextInput,  # 添加参数模式
        ),
        StructuredTool(
            name="generate_creative_text",
            description="生成创意文案，包括故事、剧本、诗歌等",
            func=_generate_creative_text,
            args_schema=CreativeTextInput,  # 添加参数模式
        ),
    ]

    return tools


__all__ = ["load_text_tools"]
