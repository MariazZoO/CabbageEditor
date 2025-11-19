# ============================================================================
# 视频生成后端测试示例
# ============================================================================

import sys
import json
from pathlib import Path

IMAGE_CACHE_DIR = Path("/home/beortust/MyData/CodeLib/PythonLib/AI-Test/img_cache")

PROMPT = (
    "masterpiece, best quality, 1girl, anime style, "
    "long brown hair blowing in the wind, grey hoodie, blue skirt, "
    "standing on a high cliff, looking back, "
    "overlooking the vast ocean at sunset, "
    "beautiful sky with dramatic clouds, sun rays, "
    "cinematic lighting, wide angle, breathtaking view, "
    "reflection on water, distant mountains, peaceful"
)

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Backend.artificial_intelligence.service import handle_video_generation


def test_video_generation_service():
    """测试视频生成服务的基本功能"""

    # 发送测试请求
    payload = {
        "prompt": PROMPT,
        "image_url": str(IMAGE_CACHE_DIR / "7be4ecf5a1e14473827038e5f6507472.png"),
        "resolution": "720P",
        "prompt_extend": True,
    }

    print("=" * 60)
    print("视频生成服务测试")
    print("=" * 60)
    print("\n发送请求:")
    print(f"  提示词: {payload['prompt'][:50]}...")
    print(f"  图像: {payload['image_url']}")
    print(f"  分辨率: {payload['resolution']}")

    # 调用服务接口
    response_json = handle_video_generation(payload)
    data = json.loads(response_json)

    print("\n收到响应:")
    print(f"  状态: {data.get('status')}")

    if data.get("status") == "success":
        print(f"  提示词: {data.get('prompt')}")
        print(f"  视频URL: {data.get('video_url')}")
        print(f"  任务ID: {data.get('task_id')}")
        print(f"  分辨率: {data.get('resolution')}")
        if data.get('usage'):
            usage = data['usage']
            print("\n  资源使用:")
            print(f"    视频时长: {usage.get('video_duration')}秒")
            print(f"    图片数量: {usage.get('num_images')}")
    else:
        print(f"  错误: {data.get('content')}")


if __name__ == "__main__":
    test_video_generation_service()
