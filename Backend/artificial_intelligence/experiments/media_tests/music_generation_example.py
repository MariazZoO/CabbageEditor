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
    from Backend.artificial_intelligence.tools.base import load_tools
    from Backend.artificial_intelligence.config.config import get_app_config

    print("=" * 60)
    print("音乐生成测试 - 快速模式")
    print("=" * 60)

    try:
        # 加载配置和工具
        config = get_app_config()
        tools = load_tools(config)

        # 查找音乐生成工具
        music_tool = None
        for tool in tools:
            if tool.name == "generate_bgm_music":
                music_tool = tool
                break

        if not music_tool:
            print("✗ 未找到音乐生成工具")
            print("  请检查:")
            print("  1. 是否配置了 suno provider")
            print("  2. 是否设置了 SUNO_API_KEY 环境变量")
            return None

        # 测试参数
        payload = {
            "prompt": "轻松愉快的钢琴曲，适合学习和工作",
            "style": "lofi",
            "model": "V5",
            "duration": 20,
            "wait": False,  # 不等待完成,立即返回
            "session_id": "test_session",
        }

        print("\n发送请求:")
        print(f"  提示词: {payload['prompt']}")
        print(f"  风格: {payload['style']}")
        print(f"  模型: {payload['model']}")
        print(f"  时长: {payload['duration']}秒")

        # 调用工具
        result = music_tool.invoke(payload)
        data = json.loads(result)

        print("\n收到响应:")
        print(f"  状态: {data.get('status')}")
        print(f"  任务ID: {data.get('task_id')}")
        print(f"  会话ID: {data.get('session_id')}")

        if data.get("status") in ["submitted", "pending"]:
            print("\n✓ 任务提交成功！")
            print("  可以使用 task_id 查询生成进度")
            return data.get("task_id")
        else:
            print(f"\n⚠ 意外状态: {data.get('status')}")
            if data.get("error"):
                print(f"  错误: {data.get('error')}")
            return None

    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


def test_music_generation_with_wait():
    """测试同步音乐生成（等待完成并下载）"""
    from Backend.artificial_intelligence.tools.base import load_tools
    from Backend.artificial_intelligence.config.config import get_app_config

    print("\n" + "=" * 60)
    print("音乐生成测试 - 同步等待模式")
    print("=" * 60)
    print("⚠ 注意：此测试会等待音乐生成完成，可能需要几分钟")

    try:
        # 加载配置和工具
        config = get_app_config()
        tools = load_tools(config)

        # 查找音乐生成工具
        music_tool = None
        for tool in tools:
            if tool.name == "generate_bgm_music":
                music_tool = tool
                break

        if not music_tool:
            print("✗ 未找到音乐生成工具")
            return

        # 测试参数
        payload = {
            "prompt": "史诗级电影配乐，气势磅礴",
            "style": "epic orchestral",
            "model": "V5",
            "duration": 10,
            "wait": True,  # 等待完成
            "max_wait_seconds": 600,  # 最多等待5分钟
            "poll_interval": 5.0,  # 每5秒查询一次
            "session_id": "test_session",
        }

        print("\n发送请求:")
        print(f"  提示词: {payload['prompt']}")
        print(f"  风格: {payload['style']}")
        print(f"  时长: {payload['duration']}秒")
        print(f"  最大等待: {payload['max_wait_seconds']}秒")

        # 调用工具
        print("\n开始生成，请稍候...")
        result = music_tool.invoke(payload)
        data = json.loads(result)

        print("\n收到响应:")
        print(f"  状态: {data.get('status')}")

        # 调试：打印完整响应
        print("\n完整响应数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        if data.get("status") in ["succeeded", "completed", "SUCCESS", "FIRST_SUCCESS"]:
            print("\n✓ 音乐生成成功！")

            # 显示音频数量
            audio_count = data.get("audio_count", 0)
            if audio_count:
                print(f"\n  生成了 {audio_count} 首音乐")

            # 显示所有音频信息
            audio_list = data.get("audio_list", [])
            if audio_list:
                print("\n  音频列表:")
                for audio in audio_list:
                    print(f"\n  [{audio.get('index')}] {audio.get('title', '未命名')}")
                    print(f"    • ID: {audio.get('id')}")
                    print(f"    • 时长: {audio.get('duration')}秒")
                    print(f"    • 标签: {audio.get('tags')}")
                    print(f"    • 源URL: {audio.get('source_url')}")
                    print(f"    • 本地路径: {audio.get('local_path')}")
                    print(f"    • 自动保存URL: {audio.get('autosave_url')}")
                    file_size_mb = audio.get("file_size_bytes", 0) / 1024 / 1024
                    print(f"    • 文件大小: {file_size_mb:.2f} MB")

                    # 检查文件是否存在
                    local_path = audio.get("local_path")
                    if local_path and Path(local_path).exists():
                        print("    ✅ 文件已保存")
                    else:
                        print("    ⚠ 文件未找到")
        else:
            print("\n✗ 生成失败或超时")
            print(f"  状态: {data.get('status')}")
            if data.get("error"):
                print(f"  错误: {data.get('error')}")

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
