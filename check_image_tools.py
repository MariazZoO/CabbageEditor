#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
图像工具检查和测试脚本

使用方式:
  python check_image_tools.py
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))


def main():
    print("\n" + "="*70)
    print("🖼️  图像工具加载和调用检查")
    print("="*70 + "\n")

    # 测试1: 加载配置
    print("📋 [测试 1] 加载配置")
    print("-" * 70)

    try:
        from Backend.utils.bootstrap import bootstrap
        bootstrap()

        from Backend.artificial_intelligence.config.config import get_app_config
        config = get_app_config()

        print("✅ 配置加载成功")
        print(f"   图像工具启用: {config.media.image.enable}")
        print(f"   提供商: {config.media.image.provider}")
        print(f"   模型: {config.media.image.model}")

    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

    # 测试2: 加载图像工具
    print("\n📋 [测试 2] 加载图像工具")
    print("-" * 70)

    try:
        from Backend.artificial_intelligence.tools.media.image_tools import (
            load_image_tools,
            ImageGenerationInput,
        )

        image_tools = load_image_tools(config)

        if image_tools:
            print(f"✅ 图像工具加载成功，共 {len(image_tools)} 个")
            for tool in image_tools:
                print(f"   - {tool.name}: {tool.description[:60]}...")
        else:
            print("⚠️  未加载到图像工具，请检查配置")
            return False

    except Exception as e:
        print(f"❌ 图像工具加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试3: 加载所有工具
    print("\n📋 [测试 3] 加载所有工具")
    print("-" * 70)

    try:
        from Backend.artificial_intelligence.tools import load_tools

        all_tools = load_tools(config)
        print(f"✅ 工具加载成功，共 {len(all_tools)} 个:")

        for i, tool in enumerate(all_tools, 1):
            tool_type = "📸" if tool.name == "generate_image" else "🔧"
            print(f"   {i}. {tool_type} {tool.name}")

    except Exception as e:
        print(f"❌ 工具加载失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试4: 代理创建
    print("\n📋 [测试 4] 代理创建")
    print("-" * 70)

    try:
        from Backend.artificial_intelligence.agent.factory import (
            create_default_agent,
        )

        agent = create_default_agent(force_reload=True)
        print("✅ 代理创建成功")
        print(f"   类型: {type(agent).__name__}")

    except Exception as e:
        print(f"❌ 代理创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试5: 输入验证
    print("\n📋 [测试 5] 输入验证")
    print("-" * 70)

    try:
        # 测试有效输入
        valid = ImageGenerationInput(prompt="测试提示词")
        print("✅ 有效输入验证通过")
        print(f"   prompt: {valid.prompt}")

        # 测试无效输入
        try:
            ImageGenerationInput()
            print("⚠️  应该验证失败，但未失败")
        except Exception:
            print("✅ 无效输入正确拒绝（缺少必需字段）")

    except Exception as e:
        print(f"❌ 输入验证失败: {e}")
        return False

    # 总结
    print("\n" + "="*70)
    print("✅ 所有检查均通过")
    print("="*70 + "\n")

    print("\n📊 检查摘要:")
    print("   ✅ 配置加载: 成功")
    print("   ✅ 图像工具: 已加载")
    print("   ✅ 工具系统: 正常")
    print("   ✅ 代理创建: 成功")
    print("   ✅ 输入验证: 正常")

    print("\n💡 提示:")
    print("   - 图像工具已准备好被 LLM Agent 调用")
    print("   - 支持三种模式：纯文本生成、图片编辑、自动引用")
    print("   - 详见: docs/IMAGE_TOOLS_CHECK_REPORT.md\n")

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
