"""
文案生成工具 - 使用豆包 LLM 专职生成各类文案内容
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage, SystemMessage

from Backend.artificial_intelligence.config.ai_config import AIConfig
from Backend.artificial_intelligence.models import get_chat_model


# 定义参数模式
class ProductCopywritingInput(BaseModel):
    """产品文案生成的输入参数"""
    product_name: str = Field(description="产品名称")
    product_features: str = Field(description="产品特点或卖点，用逗号分隔")
    style: str = Field(default="专业", description="文案风格，可选：专业、活泼、高端、亲切、幽默")
    length: str = Field(default="中等", description="文案长度，可选：简短、中等、详细")


class MarketingCopywritingInput(BaseModel):
    """营销文案生成的输入参数"""
    theme: str = Field(description="营销主题，如：618大促、新品发布、会员日等")
    target_audience: str = Field(description="目标受众，如：年轻人、企业主、家庭用户等")
    key_points: str = Field(description="营销要点，用逗号分隔")
    platform: str = Field(default="通用", description="投放平台，可选：通用、微信、微博、抖音、小红书")
    tone: str = Field(default="激励", description="文案语气，可选：激励、温暖、紧迫、趣味")


class CreativeCopywritingInput(BaseModel):
    """创意文案生成的输入参数"""
    content_type: str = Field(description="内容类型，如：故事、诗歌、剧本、广告语、slogan等")
    theme: str = Field(description="创作主题")
    keywords: Optional[str] = Field(default=None, description="关键词，用逗号分隔（可选）")
    style: str = Field(default="现代", description="创作风格，可选：现代、古典、浪漫、科技、悬疑等")
    length: str = Field(default="中等", description="作品长度，可选：简短、中等、长篇")


def load_copywriting_tools(config: AIConfig) -> List[StructuredTool]:
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

    def _generate_product_copywriting(
        product_name: str,
        product_features: str,
        style: str = "专业",
        length: str = "中等",
    ) -> str:
        """
        生成产品文案

        Args:
            product_name: 产品名称
            product_features: 产品特点或卖点（用逗号分隔）
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
请为以下产品生成{style}风格的文案，长度约{length_map.get(length, '150-200字')}：

产品名称：{product_name}
产品特点：{product_features}

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

        response = llm.invoke(messages)
        return response.content

    def _generate_marketing_copywriting(
        theme: str,
        target_audience: str,
        key_points: str,
        platform: str = "通用",
        tone: str = "激励",
    ) -> str:
        """
        生成营销文案

        Args:
            theme: 营销主题（如：618大促、新品发布、会员日等）
            target_audience: 目标受众（如：年轻人、企业主、家庭用户等）
            key_points: 营销要点（用逗号分隔）
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
请为以下营销活动生成{tone}语气的文案：

营销主题：{theme}
目标受众：{target_audience}
营销要点：{key_points}
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

        response = llm.invoke(messages)
        return response.content

    def _generate_creative_copywriting(
        content_type: str,
        theme: str,
        keywords: Optional[str] = None,
        style: str = "现代",
        length: str = "中等",
    ) -> str:
        """
        生成创意文案

        Args:
            content_type: 内容类型（如：故事、诗歌、剧本、广告语、slogan等）
            theme: 创作主题
            keywords: 关键词（可选，用逗号分隔）
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

        keywords_text = f"\n关键词：{keywords}" if keywords else ""

        prompt = f"""
请创作一个{style}风格的{content_type}：

创作主题：{theme}{keywords_text}
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

        response = llm.invoke(messages)
        return response.content

    # 创建三个结构化工具，带有明确的参数模式
    tools = [
        StructuredTool(
            name="generate_product_copywriting",
            description=(
                "生成产品文案。用于创作产品描述、卖点提炼、产品广告语等。"
                "适用场景：电商产品详情页、产品手册、宣传册等。"
            ),
            func=_generate_product_copywriting,
            args_schema=ProductCopywritingInput,
        ),
        StructuredTool(
            name="generate_marketing_copywriting",
            description=(
                "生成营销文案。用于创作活动宣传、促销文案、社交媒体内容等。"
                "适用场景：营销活动推广、社交媒体运营、广告投放等。"
            ),
            func=_generate_marketing_copywriting,
            args_schema=MarketingCopywritingInput,
        ),
        StructuredTool(
            name="generate_creative_copywriting",
            description=(
                "生成创意文案。用于创作故事、诗歌、剧本、slogan等各类创意内容。"
                "适用场景：品牌故事、创意广告、内容营销等。"
            ),
            func=_generate_creative_copywriting,
            args_schema=CreativeCopywritingInput,
        ),
    ]

    return tools


__all__ = ["load_copywriting_tools"]
