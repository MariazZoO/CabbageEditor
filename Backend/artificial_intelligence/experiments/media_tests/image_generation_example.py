# ============================================================================
# 图像生成服务测试示例 - 简化版
# ============================================================================
import sys
import json
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Backend.artificial_intelligence.service import handle_image_generation


def test_image_generation():
    """直接测试图像生成功能"""
    payload = {"prompt": "一只可爱的奶牛猫，写实风格", "session_id": "test_session"}

    print(f"发送请求: {payload}")

    try:
        result = handle_image_generation(payload)
        data = json.loads(result)

        print("\n收到响应:")
        print(f"  状态: {data.get('status')}")
        if data.get("status") == "success":
            print(f"  提示词: {data.get('prompt')}")
            print(f"  图像名: {data['image']['name']}")
            print(f"  图像路径: {data['image']['path']}")
            return data["image"]["url"]  # 返回图片 URL
        else:
            print(f"  错误: {data.get('content')}")
            return None
    except Exception as e:
        print(f"图像生成失败: {e}")
        return None


def test_image_edit(image_url):
    """测试图像编辑功能"""

    if not image_url:
        print("未提供图片，跳过测试")
        return

    payload = {
        "prompt": "将这张图片变成卡通风格",
        "session_id": "test_session",
        "product_url": image_url,  # 使用测试1生成的图片
        "use_references": True,
    }

    print("\n发送图片编辑请求")
    print(f"  输入图片: {image_url}")
    print(f"  编辑提示: {payload['prompt']}")

    try:
        result = handle_image_generation(payload)
        data = json.loads(result)

        print("\n收到响应:")
        print(f"  状态: {data.get('status')}")
        if data.get("status") == "success":
            print(f"  提示词: {data.get('prompt')}")
            print(f"  编辑后图像: {data['image']['name']}")
            print(f"  保存路径: {data['image']['path']}")
        else:
            print(f"  错误: {data.get('content')}")
    except Exception as e:
        print(f"图像编辑失败: {e}")


if __name__ == "__main__":
    # 测试 1: 文生图
    print("\n【测试 1】文生图")
    print("-" * 60)
    generated_image_url = test_image_generation()

    # 测试 2: 图片编辑（使用测试1的输出）
    print("\n【测试 2】图片编辑")
    print("-" * 60)
    test_image_edit(generated_image_url)
