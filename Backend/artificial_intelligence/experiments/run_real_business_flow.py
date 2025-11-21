import os
import sys
import json
import time
import base64
from pathlib import Path

# 1. 设置项目根目录路径
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# 导入服务接口
from Backend.artificial_intelligence.service.text import handle_text_generation
from Backend.artificial_intelligence.service.image import handle_image_generation
from Backend.artificial_intelligence.service.video import handle_video_generation
from Backend.artificial_intelligence.service.speech import handle_speech_generation
from Backend.artificial_intelligence.service.music import handle_music_generation
from Backend.artificial_intelligence.service.integrated import (
    handle_integrated_entrance,
)

# 导入配置检查
from Backend.artificial_intelligence.config.ai_config import get_ai_config


def print_separator(title):
    print("\n" + "=" * 60)
    print(f" {title} ")
    print("=" * 60)


def print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))


def run_service_test(service_name, handler_func, payload):
    print_separator(f"Testing {service_name}")
    print(f"Input Payload: {json.dumps(payload, ensure_ascii=False)}")

    start_time = time.time()
    try:
        response_str = handler_func(payload)
        duration = time.time() - start_time

        try:
            response_data = json.loads(response_str)
            print(f"\nResponse (Time: {duration:.2f}s):")
            print_json(response_data)

            if response_data.get("error_code", 0) != 0:
                print(
                    f"\n[FAILED] {service_name} returned error: {response_data.get('status_info')}"
                )
                return None

            return response_data
        except json.JSONDecodeError:
            print(f"\n[FAILED] Invalid JSON response: {response_str}")
            return None

    except Exception as e:
        print(f"\n[ERROR] Exception during {service_name}: {e}")
        import traceback

        traceback.print_exc()
        return None


def main():
    print("Starting Real Business Flow Test...")

    # 检查配置
    config = get_ai_config()
    print(f"Loaded AI Config. Providers: {list(config.providers.keys())}")

    session_id = f"test_session_{int(time.time())}"  # 1. 文本生成测试
    text_payload = {
        "session_id": session_id,
        "llm_content": [
            {
                "role": "user",
                "part": [
                    {
                        "content_type": "text",
                        "content_text": "请为一款名为'星际咖啡'的咖啡品牌写一句广告语，要体现未来感。",
                    }
                ],
            }
        ],
        "metadata": {},
    }
    text_result = run_service_test(
        "Text Generation", handle_text_generation, text_payload
    )

    # 2. 图像生成测试
    image_payload = {
        "session_id": session_id,
        "llm_content": [
            {
                "role": "user",
                "part": [
                    {
                        "content_type": "text",
                        "content_text": "一个漂浮在太空中的未来咖啡馆，透过巨大的玻璃窗可以看到绚丽的星云，赛博朋克风格，高清晰度",
                        "parameter": {"resolution": "1:1", "style": "cyberpunk"},
                    }
                ],
            }
        ],
        "metadata": {},
    }
    image_result = run_service_test(
        "Image Generation", handle_image_generation, image_payload
    )

    generated_image_url = None
    if image_result and image_result.get("llm_content"):
        parts = image_result["llm_content"][0].get("part", [])
        if parts:
            generated_image_url = parts[0].get("content_url")
            print(f"\nGot Generated Image URL: {generated_image_url}")

    # 3. 视频生成测试 (依赖图像)
    if generated_image_url:
        video_payload = {
            "session_id": session_id,
            "llm_content": [
                {
                    "role": "user",
                    "part": [
                        {
                            "content_type": "text",
                            "content_text": "镜头缓慢推进，可以看到咖啡馆里的机器人在忙碌，星云在背景中缓慢流动",
                            "parameter": {
                                "resolution": "720P",
                            },
                        },
                        {
                            "content_type": "image",
                            "content_url": generated_image_url,
                        },
                    ],
                }
            ],
            "metadata": {},
        }
        run_service_test("Video Generation", handle_video_generation, video_payload)
    else:
        print_separator("Skipping Video Generation (No Image Generated)")

    # 4. 语音生成测试
    speech_payload = {
        "session_id": session_id,
        "llm_content": [
            {
                "role": "user",
                "part": [
                    {
                        "content_type": "text",
                        "content_text": "欢迎来到星际咖啡，品味来自银河系的味道。",
                        "parameter": {
                            "timbre": "male_tech"  # 假设的音色参数，具体取决于实现
                        },
                    }
                ],
            }
        ],
        "metadata": {},
    }
    run_service_test("Speech Generation", handle_speech_generation, speech_payload)

    # 5. 综合对话测试
    integrated_payload = {
        "session_id": session_id,
        "llm_content": [
            {
                "role": "user",
                "part": [
                    {
                        "content_type": "text",
                        "content_text": "帮我构思一个关于'失落的古代文明'的短篇故事梗概，然后为这个故事生成一张神秘的封面图。",
                    }
                ],
            }
        ],
        "metadata": {},
    }
    run_service_test(
        "Integrated Dialogue", handle_integrated_entrance, integrated_payload
    )

    # 6. 音乐生成测试
    music_payload = {
        "session_id": session_id,
        "llm_content": [
            {
                "role": "user",
                "part": [
                    {
                        "content_type": "text",
                        "content_text": "轻松的爵士乐，带有未来感的电子音效，适合咖啡馆背景音乐",
                        "parameter": {"duration": 15},
                    }
                ],
            }
        ],
        "metadata": {},
    }
    run_service_test("Music Generation", handle_music_generation, music_payload)


if __name__ == "__main__":
    main()
