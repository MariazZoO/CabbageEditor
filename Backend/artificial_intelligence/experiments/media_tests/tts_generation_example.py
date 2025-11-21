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
    from Backend.artificial_intelligence.service import handle_speech_generation
    import json

    print("=" * 60)
    print("语音合成工具 (TTS) 测试")
    print("=" * 60)

    try:
        # 测试工具调用
        print("\n5. 测试工具调用...")
        print('  调用: handle_speech_generation(text="你好世界")')

        payload = {
            "session_id": "test_session",
            "llm_content": [
                {
                    "role": "user",
                    "interface_type": "speech",
                    "part": [{"content_type": "text", "content_text": "你好世界"}],
                    "parameter": {
                        "voice_type": "zh_female_cancan_mars_bigtts",
                        "speed_ratio": 1.0,
                        "loudness_ratio": 1.0,
                        "encoding": "mp3",
                        "rate": 24000,
                        "max_wait_seconds": 60,
                        "poll_interval": 2.0,
                    },
                }
            ],
        }

        try:
            # 注意：这会发送真实的 HTTP 请求到火山引擎（异步模式）
            result = handle_speech_generation(payload)

            print("  结果:")
            result_data = json.loads(result)
            print(f"    状态码: {result_data.get('error_code')}")

            if result_data.get("error_code") == 0:
                llm_content = result_data.get("llm_content", [])
                if llm_content:
                    parts = llm_content[0].get("part", [])
                    for part in parts:
                        if part.get("content_type") == "audio":
                            print(f"    音频URL: {part.get('content_url')}")
                            params = part.get("parameter", {})
                            print(f"    时长: {params.get('duration')}s")

                metadata = result_data.get("metadata", {})
                print(f"    任务ID: {metadata.get('task_id')}")
                print("\n✓ TTS 工具测试成功！")
                return True
            else:
                print(f"    错误: {result_data.get('status_info')}")
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


if __name__ == "__main__":
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
