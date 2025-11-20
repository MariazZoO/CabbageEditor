"""
测试所有服务接口
快速验证图像、视频、文案、TTS、音乐生成等服务接口
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Backend.artificial_intelligence.service import (
    handle_image_generation,
    handle_video_generation,
    handle_text_generation,
    handle_speech_generation,
    handle_music_generation,
)


def test_text_service():
    """测试文案生成服务"""
    print("\n" + "=" * 60)
    print("测试 1: 文案生成服务")
    print("=" * 60)

    # 测试产品文案
    print("\n【产品文案】")
    payload = {
        "type": "product",
        "product_name": "智能手表X1",
        "product_features": "心率监测,运动追踪,超长待机,防水设计",
        "style": "专业",
        "length": "中等",
    }

    try:
        result = handle_text_generation(payload)
        data = json.loads(result)

        print(f"状态: {data.get('status')}")
        if data.get("status") == "success":
            print(f"文案类型: {data.get('copywriting_type')}")
            print(f"生成内容:\n{data.get('content')}")
        else:
            print(f"错误: {data.get('content')}")
    except Exception as e:
        print(f"测试失败: {e}")


def test_speech_service():
    """测试TTS服务"""
    print("\n" + "=" * 60)
    print("测试 2: TTS语音合成服务")
    print("=" * 60)

    payload = {
        "text": "欢迎使用智能语音助手",
        "voice_type": "zh_female_cancan_mars_bigtts",
        "speed_ratio": 1.0,
        "encoding": "mp3",
        "max_wait_seconds": 30,
    }

    try:
        result = handle_speech_generation(payload)
        data = json.loads(result)

        print(f"状态: {data.get('status')}")
        if data.get("status") == "success":
            print(f"任务ID: {data.get('task_id')}")
            print(f"音频URL: {data.get('audio_url')}")
            print(f"时长: {data.get('duration')}ms")
            print(f"音色: {data.get('voice_type')}")
        else:
            print(f"错误: {data.get('content')}")
    except Exception as e:
        print(f"测试失败: {e}")


def test_music_service():
    """测试音乐生成服务（快速模式）"""
    print("\n" + "=" * 60)
    print("测试 3: BGM音乐生成服务（快速模式）")
    print("=" * 60)

    payload = {
        "prompt": "轻松愉快的钢琴曲",
        "style": "lofi",
        "model": "V5",
        "duration": 10,
        "wait": False,  # 快速返回，不等待完成
    }

    try:
        result = handle_music_generation(payload)
        data = json.loads(result)

        print(f"状态: {data.get('status')}")
        print(f"任务ID: {data.get('task_id')}")
        if data.get("status") in ["pending", "submitted"]:
            print("✓ 任务提交成功，可使用task_id查询进度")
        elif data.get("audio_list"):
            print(f"音频数量: {data.get('audio_count')}")
            for audio in data.get("audio_list", []):
                print(f"  - {audio.get('title')}: {audio.get('audio_url')}")
        else:
            print(f"内容: {data.get('content', 'N/A')}")
    except Exception as e:
        print(f"测试失败: {e}")


def test_image_service():
    """测试图像生成服务"""
    print("\n" + "=" * 60)
    print("测试 4: 图像生成服务")
    print("=" * 60)

    payload = {
        "prompt": "一只可爱的小猫咪",
    }

    try:
        result = handle_image_generation(payload)
        data = json.loads(result)

        print(f"状态: {data.get('status')}")
        if data.get("status") == "success":
            image_info = data.get("image", {})
            print(f"提示词: {data.get('prompt')}")
            print(f"图像URL: {image_info.get('url')}")

            return image_info.get("url")  # 返回图像URL供视频测试使用
        else:
            print(f"错误: {data.get('content')}")
            return None
    except Exception as e:
        print(f"测试失败: {e}")
        return None


def test_video_service(image_url=None):
    """测试视频生成服务"""
    print("\n" + "=" * 60)
    print("测试 5: 视频生成服务")
    print("=" * 60)

    if not image_url:
        print("跳过视频测试，因为没有可用的图像URL")
        return

    payload = {
        "prompt": "镜头缓慢推进，小猫咪在阳光下打哈欠，温馨可爱的画面",
        "image_url": image_url,
        "resolution": "720P",
        "prompt_extend": True,
    }

    try:
        result = handle_video_generation(payload)
        data = json.loads(result)

        print(f"状态: {data.get('status')}")
        if data.get("status") == "success":
            print(f"提示词: {data.get('prompt')}")
            print(f"视频URL: {data.get('video_url')}")
            print(f"任务ID: {data.get('task_id')}")
            print(f"分辨率: {data.get('resolution')}")
            if data.get("usage"):
                usage = data["usage"]
                print("\n  资源使用:")
                print(f"    视频时长: {usage.get('video_duration')}秒")
                print(f"    图片数量: {usage.get('num_images')}")
        else:
            print(f"错误: {data.get('content')}")
    except Exception as e:
        print(f"测试失败: {e}")


if __name__ == "__main__":
    print("\n🎯 服务接口测试套件")
    print("=" * 60)

    # 测试顺序：从简单到复杂
    test_text_service()
    test_speech_service()
    test_music_service()

    # 图像生成，并获取URL用于视频测试
    image_url = test_image_service()

    # 使用生成的图像URL进行视频测试
    test_video_service(image_url)

    print("\n" + "=" * 60)
    print("✓ 所有测试完成")
    print("=" * 60)
