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


def test_image_generation():
    from Backend.artificial_intelligence.service import handle_image_generation
    """直接测试图像生成功能"""
    payload = {
        "session_id": "test_session",
        "llm_content": [
            {
                "role": "user",
                "interface_type": "image",
                "part": [
                    {
                        "content_type": "text",
                        "content_text": "一只可爱的奶牛猫，写实风格",
                    }
                ],
            }
        ],
    }

    print(f"发送请求: {json.dumps(payload, ensure_ascii=False)}")

    try:
        result = handle_image_generation(payload)
        data = json.loads(result)

        print("\n收到响应:")
        print(f"  状态码: {data.get('error_code')}")
        if data.get("error_code") == 0:
            llm_content = data.get("llm_content", [])
            if llm_content:
                parts = llm_content[0].get("part", [])
                for part in parts:
                    if part.get("content_type") == "image":
                        print(f"  图像URL: {part.get('content_url')}")
                        return part.get("content_url")
            print("  未找到图像内容")
            return None
        else:
            print(f"  错误: {data.get('status_info')}")
            return None
    except Exception as e:
        print(f"图像生成失败: {e}")
        return None


def test_image_edit(image_url):
    from Backend.artificial_intelligence.service import handle_image_generation
    """测试图像编辑功能"""

    if not image_url:
        print("未提供图片，跳过测试")
        return

    payload = {
        "session_id": "test_session",
        "llm_content": [
            {
                "role": "user",
                "interface_type": "image",
                "part": [
                    {
                        "content_type": "text",
                        "content_text": "将这张图片变成卡通风格",
                        "parameter": {"product_url": image_url},
                    }
                ],
            }
        ],
    }

    print("\n发送图片编辑请求")
    print(f"  输入图片: {image_url[:50]}...")
    print(f"  编辑提示: {payload['llm_content'][0]['part'][0]['content_text']}")

    try:
        result = handle_image_generation(payload)
        data = json.loads(result)

        print("\n收到响应:")
        print(f"  状态码: {data.get('error_code')}")
        if data.get("error_code") == 0:
            llm_content = data.get("llm_content", [])
            if llm_content:
                parts = llm_content[0].get("part", [])
                for part in parts:
                    if part.get("content_type") == "image":
                        print(f"  编辑后图像URL: {part.get('content_url')}")
        else:
            print(f"  错误: {data.get('status_info')}")
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
