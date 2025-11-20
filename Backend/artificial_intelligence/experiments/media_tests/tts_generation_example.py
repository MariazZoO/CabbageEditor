"""
语音合成工具测试脚本
测试 TTS 工具的基本功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
# 从 Backend/artificial_intelligence/experiments/media_tests/ 到项目根目录
repo_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(repo_root))


def test_tts_tools():
    """测试 TTS 工具"""
    from Backend.artificial_intelligence.config.ai_config import get_ai_config
    from Backend.artificial_intelligence.tools.base import load_tools

    print("=" * 60)
    print("语音合成工具 (TTS) 测试")
    print("=" * 60)

    try:
        # 加载配置
        print("\n1. 正在加载配置...")
        config = get_ai_config()
        print("✓ 配置加载成功")

        # 检查 TTS 配置
        print("\n2. 检查 TTS 配置...")
        if not config.tts.appid or not config.tts.token:
            print("⚠ 警告：TTS 未配置 (appid 或 token 缺失)")
            print("  请在 app_config.toml 中配置 TTS 凭证")
            print("  配置位置: [tts] 部分")
            return False
        print("✓ TTS 配置正确")
        print(f"  - AppID: {config.tts.appid[:10]}...")
        print(f"  - Token: {config.tts.token[:10]}...")

        # 加载工具
        print("\n3. 正在加载所有工具...")
        tools = load_tools(config)
        print(f"✓ 成功加载 {len(tools)} 个工具")

        # 查找 TTS 工具
        print("\n4. 查找 text_to_speech 工具...")
        tts_tool = None
        for tool in tools:
            if tool.name == "text_to_speech":
                tts_tool = tool
                break

        if tts_tool:
            print("✓ 找到 text_to_speech 工具")
            print(f"  - 描述: {tts_tool.description}")
            print(f"  - 参数: {list(tts_tool.args_schema.model_fields.keys())}")
        else:
            print("✗ 未找到 text_to_speech 工具")
            print(f"  可用工具: {[t.name for t in tools]}")
            return False

        # 测试工具调用
        print("\n5. 测试工具调用...")
        print('  调用: text_to_speech(text="你好世界")')

        try:
            # 注意：这会发送真实的 HTTP 请求到火山引擎（异步模式）
            result = tts_tool.invoke(
                {
                    "text": "你好世界",
                    "voice_type": "zh_female_cancan_mars_bigtts",
                    "speed_ratio": 1.0,
                    "loudness_ratio": 1.0,
                    "encoding": "mp3",
                    "rate": 24000,
                    "max_wait_seconds": 60,
                    "poll_interval": 2.0,
                }
            )

            print("  结果:")
            import json
            result_data = json.loads(result)
            print(f"    状态: {result_data.get('status')}")
            print(f"    类型: {result_data.get('type')}")
            if result_data.get('audio_url'):
                print(f"    音频URL: {result_data.get('audio_url')}")
            if result_data.get('duration_ms'):
                print(f"    时长: {result_data.get('duration_ms')}ms")
            if result_data.get('error'):
                print(f"    错误: {result_data.get('error')}")

            if result_data.get('status') == 'success':
                print("\n✓ TTS 工具测试成功！")
                return True
            else:
                print("\n✗ TTS 工具返回错误")
                return False

        except Exception as e:
            print(f"  ✗ 调用失败: {str(e)}")
            print("\n  可能的原因:")
            print("  - 网络连接问题")
            print("  - 火山引擎服务不可用")
            print("  - AppID/Token 无效")
            return False

    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_import():
    """测试导入"""
    print("=" * 60)
    print("导入测试")
    print("=" * 60)

    try:
        print("\n正在测试导入...")

        print("  • 导入 tts_client...")
        from Backend.artificial_intelligence.models.client_speech import (
            create_tts_client,  # noqa: F401
            AudioConfig,  # noqa: F401
        )

        print("    ✓")

        print("  • 导入 tts_tools...")
        from Backend.artificial_intelligence.tools.media.speech_tools import (
            load_tts_tools,  # noqa: F401
        )

        print("    ✓")

        print("  • 导入配置...")
        from Backend.artificial_intelligence.config.ai_config import (
            get_ai_config,  # noqa: F401
            TTSConfig,  # noqa: F401
        )

        print("    ✓")

        print("\n✓ 所有导入成功")
        return True

    except Exception as e:
        print(f"\n✗ 导入失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 首先测试导入
    if not test_import():
        sys.exit(1)

    print("\n")

    # 然后测试工具
    if not test_tts_tools():
        print("\n⚠ 注意: 如果上面显示 'TTS 未配置'，请按照以下步骤配置:")
        print(
            "  1. 访问 https://www.volcengine.com/docs/6561/196768 获取 AppID 和 Token"
        )
        print("  2. 编辑 Backend/artificial_intelligence/config/app_config.toml")
        print("  3. 在 [tts] 部分添加:")
        print('     appid = "your-appid"')
        print('     token = "your-token"')
        print("  4. 重新运行此脚本")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)
