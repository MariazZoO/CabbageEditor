"""
文案生成工具测试脚本

测试豆包LLM文案生成功能的各种场景
"""

from __future__ import annotations

import sys
from pathlib import Path

# 添加项目路径
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))

from Backend.artificial_intelligence.config.config import get_app_config
from Backend.artificial_intelligence.tools.copywriting import load_copywriting_tools


def test_product_copywriting():
    """测试产品文案生成"""
    print("\n" + "=" * 50)
    print("测试1: 产品文案生成")
    print("=" * 50)

    config = get_app_config()
    tools = load_copywriting_tools(config)

    if not tools:
        print("❌ 文案生成工具加载失败，请检查豆包provider配置")
        return

    # 查找产品文案工具
    product_tool = next(
        (t for t in tools if t.name == "generate_product_copywriting"), None
    )
    if not product_tool:
        print("❌ 未找到产品文案生成工具")
        return

    print("\n正在生成产品文案...")
    try:
        result = product_tool.invoke(
            {
                "product_name": "智能降噪耳机 AirPods Pro",
                "product_features": "主动降噪、空间音频、通透模式、长续航",
                "style": "专业",
                "length": "中等",
            }
        )
        print(f"\n生成的产品文案：\n{result}")
        print("\n✅ 产品文案生成成功")
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")


def test_marketing_copywriting():
    """测试营销文案生成"""
    print("\n" + "=" * 50)
    print("测试2: 营销文案生成")
    print("=" * 50)

    config = get_app_config()
    tools = load_copywriting_tools(config)

    if not tools:
        print("❌ 文案生成工具加载失败")
        return

    # 查找营销文案工具
    marketing_tool = next(
        (t for t in tools if t.name == "generate_marketing_copywriting"), None
    )
    if not marketing_tool:
        print("❌ 未找到营销文案生成工具")
        return

    print("\n正在生成营销文案...")
    try:
        result = marketing_tool.invoke(
            {
                "theme": "双十一购物节",
                "target_audience": "年轻人",
                "key_points": "全场五折、满减优惠、限时秒杀",
                "platform": "小红书",
                "tone": "激励",
            }
        )
        print(f"\n生成的营销文案：\n{result}")
        print("\n✅ 营销文案生成成功")
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")


def test_creative_copywriting():
    """测试创意文案生成"""
    print("\n" + "=" * 50)
    print("测试3: 创意文案生成")
    print("=" * 50)

    config = get_app_config()
    tools = load_copywriting_tools(config)

    if not tools:
        print("❌ 文案生成工具加载失败")
        return

    # 查找创意文案工具
    creative_tool = next(
        (t for t in tools if t.name == "generate_creative_copywriting"), None
    )
    if not creative_tool:
        print("❌ 未找到创意文案生成工具")
        return

    print("\n正在生成创意文案...")
    try:
        result = creative_tool.invoke(
            {
                "content_type": "广告语",
                "theme": "环保理念",
                "keywords": "绿色、未来、科技",
                "style": "现代",
                "length": "简短",
            }
        )
        print(f"\n生成的创意文案：\n{result}")
        print("\n✅ 创意文案生成成功")
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print(" 豆包LLM文案生成工具测试")
    print("=" * 60)

    print("\n注意：请确保已在 app_config.toml 中配置了豆包API密钥")

    # 运行测试
    test_product_copywriting()
    test_marketing_copywriting()
    test_creative_copywriting()

    print("\n" + "=" * 60)
    print(" 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
