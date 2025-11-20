"""
文案生成工具测试脚本

测试豆包LLM文案生成功能的各种场景
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

# 添加项目路径
REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT))


def test_product_text():
    from Backend.artificial_intelligence.service import handle_text_generation

    """测试产品文案生成"""
    print("\n" + "=" * 50)
    print("测试1: 产品文案生成")
    print("=" * 50)

    config = get_ai_config()
    tools = load_text_tools(config)

    if not tools:
        print("❌ 文案生成工具加载失败，请检查豆包provider配置")
        return

    # 查找产品文案工具
    product_tool = next(
        (t for t in tools if t.name == "generate_product_text"), None
    )
    if not product_tool:
        print("❌ 未找到产品文案生成工具")
        return

    print("\n正在生成产品文案...")
    payload = {
        "session_id": "test_session",
        "llm_content": [
            {
                "role": "user",
                "interface_type": "text",
                "part": [
                    {
                        "content_type": "text",
                        "content_text": "产品名：智能降噪耳机 AirPods Pro\n特点：主动降噪、空间音频、通透模式、长续航",
                    }
                ],
                "parameter": {
                    "text_type": "product",
                    "style": "专业",
                    "length": "中等",
                },
            }
        ],
    }

    try:
        result = handle_text_generation(payload)
        data = json.loads(result)

        if data.get("error_code") == 0:
            llm_content = data.get("llm_content", [])
            if llm_content:
                parts = llm_content[0].get("part", [])
                for part in parts:
                    if part.get("content_type") == "text":
                        print(f"\n生成的产品文案：\n{part.get('content_text')}")
            print("\n✅ 产品文案生成成功")
        else:
            print(f"\n❌ 生成失败: {data.get('status_info')}")
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")


def test_marketing_text():
    """测试营销文案生成"""
    print("\n" + "=" * 50)
    print("测试2: 营销文案生成")
    print("=" * 50)

    config = get_ai_config()
    tools = load_text_tools(config)

    if not tools:
        print("❌ 文案生成工具加载失败")
        return

    # 查找营销文案工具
    marketing_tool = next(
        (t for t in tools if t.name == "generate_marketing_text"), None
    )
    if not marketing_tool:
        print("❌ 未找到营销文案生成工具")
        return

    print("\n正在生成营销文案...")
    payload = {
        "session_id": "test_session",
        "llm_content": [
            {
                "role": "user",
                "interface_type": "text",
                "part": [
                    {
                        "content_type": "text",
                        "content_text": "主题：双十一购物节\n目标人群：年轻人\n卖点：全场五折、满减优惠、限时秒杀",
                    }
                ],
                "parameter": {
                    "text_type": "marketing",
                    "platform": "小红书",
                    "tone": "激励",
                },
            }
        ],
    }

    try:
        result = handle_text_generation(payload)
        data = json.loads(result)

        if data.get("error_code") == 0:
            llm_content = data.get("llm_content", [])
            if llm_content:
                parts = llm_content[0].get("part", [])
                for part in parts:
                    if part.get("content_type") == "text":
                        print(f"\n生成的营销文案：\n{part.get('content_text')}")
            print("\n✅ 营销文案生成成功")
        else:
            print(f"\n❌ 生成失败: {data.get('status_info')}")
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")


def test_creative_text():
    """测试创意文案生成"""
    print("\n" + "=" * 50)
    print("测试3: 创意文案生成")
    print("=" * 50)

    config = get_ai_config()
    tools = load_text_tools(config)

    if not tools:
        print("❌ 文案生成工具加载失败")
        return

    # 查找创意文案工具
    creative_tool = next(
        (t for t in tools if t.name == "generate_creative_text"), None
    )
    if not creative_tool:
        print("❌ 未找到创意文案生成工具")
        return

    print("\n正在生成创意文案...")
    payload = {
        "session_id": "test_session",
        "llm_content": [
            {
                "role": "user",
                "interface_type": "text",
                "part": [
                    {
                        "content_type": "text",
                        "content_text": "类型：广告语\n主题：环保理念\n关键词：绿色、未来、科技",
                    }
                ],
                "parameter": {
                    "text_type": "creative",
                    "style": "现代",
                    "length": "简短",
                },
            }
        ],
    }

    try:
        result = handle_text_generation(payload)
        data = json.loads(result)

        if data.get("error_code") == 0:
            llm_content = data.get("llm_content", [])
            if llm_content:
                parts = llm_content[0].get("part", [])
                for part in parts:
                    if part.get("content_type") == "text":
                        print(f"\n生成的创意文案：\n{part.get('content_text')}")
            print("\n✅ 创意文案生成成功")
        else:
            print(f"\n❌ 生成失败: {data.get('status_info')}")
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print(" 豆包LLM文案生成工具测试")
    print("=" * 60)

    print("\n注意：请确保已在 app_config.toml 中配置了豆包API密钥")

    # 运行测试
    test_product_text()
    test_marketing_text()
    test_creative_text()

    print("\n" + "=" * 60)
    print(" 测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
