# ============================================================================
# 音乐生成服务测试示例 - 简化版
# ============================================================================
import sys
import json
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_music_generation_quick():
    """测试快速音乐生成（不等待完成）"""
    from Backend.artificial_intelligence.service import handle_music_generation

    print("=" * 60)
    print("音乐生成测试 - 快速模式")
    print("=" * 60)

    try:
        # 测试参数
        payload = {
            "session_id": "test_session",
            "llm_content": [
                {
                    "role": "user",
                    "interface_type": "music",
                    "part": [
                        {
                            "content_type": "text",
                            "content_text": "轻松愉快的钢琴曲，适合学习和工作",
                        }
                    ],
                    "parameter": {
                        "style": "lofi",
                        "model": "V5",
                        "duration": 20,
                        "wait": False,
                    },
                }
            ],
        }

        print("\n发送请求:")
        print(f"  提示词: {payload['llm_content'][0]['part'][0]['content_text']}")
        params = payload["llm_content"][0]["parameter"]
        print(f"  风格: {params['style']}")
        print(f"  模型: {params['model']}")
        print(f"  时长: {params['duration']}秒")

        # 调用工具
        result = handle_music_generation(payload)
        data = json.loads(result)

        print("\n收到响应:")
        print(f"  状态码: {data.get('error_code')}")
        metadata = data.get("metadata", {})
        print(f"  任务ID: {metadata.get('task_id')}")
        print(f"  会话ID: {data.get('session_id')}")

        if data.get("error_code") == 0:
            print("\n✓ 任务提交成功！")
            print("  可以使用 task_id 查询生成进度")
            return metadata.get("task_id")
        else:
            print(f"\n⚠ 意外状态: {data.get('status_info')}")
            return None

    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def test_music_generation_with_wait():
    """测试同步音乐生成（等待完成并下载）"""
    from Backend.artificial_intelligence.service import handle_music_generation

    print("\n" + "=" * 60)
    print("音乐生成测试 - 同步等待模式")
    print("=" * 60)
    print("⚠ 注意：此测试会等待音乐生成完成，可能需要几分钟")

    try:
        # 测试参数
        payload = {
            "session_id": "test_session",
            "llm_content": [
                {
                    "role": "user",
                    "interface_type": "music",
                    "part": [
                        {
                            "content_type": "text",
                            "content_text": "史诗级电影配乐，气势磅礴",
                        }
                    ],
                    "parameter": {
                        "style": "epic orchestral",
                        "model": "V5",
                        "duration": 10,
                        "wait": True,
                        "max_wait_seconds": 600,
                        "poll_interval": 5.0,
                    },
                }
            ],
        }

        print("\n发送请求:")
        print(f"  提示词: {payload['llm_content'][0]['part'][0]['content_text']}")
        params = payload["llm_content"][0]["parameter"]
        print(f"  风格: {params['style']}")
        print(f"  时长: {params['duration']}秒")
        print(f"  最大等待: {params['max_wait_seconds']}秒")

        # 调用工具
        print("\n开始生成，请稍候...")
        result = handle_music_generation(payload)
        data = json.loads(result)

        print("\n收到响应:")
        print(f"  状态码: {data.get('error_code')}")

        # 调试：打印完整响应
        print("\n完整响应数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        if data.get("error_code") == 0:
            print("\n✓ 音乐生成成功！")

            llm_content = data.get("llm_content", [])
            if llm_content:
                parts = llm_content[0].get("part", [])
                print(f"\n  生成了 {len(parts)} 首音乐")

                print("\n  音频列表:")
                for i, part in enumerate(parts):
                    if part.get("content_type") == "audio":
                        print(f"\n  [{i+1}]")
                        print(f"    • URL: {part.get('content_url')}")
                        params = part.get("parameter", {})
                        print(f"    • 时长: {params.get('duration')}秒")
                        print(f"    • 风格: {params.get('music_style')}")
        else:
            print("\n✗ 生成失败或超时")
            print(f"  错误: {data.get('status_info')}")

    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断")
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("\n🎵 Suno 音乐生成测试\n")

    # 测试 1: 快速模式（立即返回）
    print("【测试 1】快速提交模式")
    print("-" * 60)
    task_id = test_music_generation_quick()

    if task_id:
        # 询问是否进行同步测试
        print("\n【测试 2】同步等待模式")
        print("-" * 60)
        test_music_generation_with_wait()

    print("\n" + "=" * 60)
    print("测试结束")
    print("=" * 60)
