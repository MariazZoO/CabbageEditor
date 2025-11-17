#!/usr/bin/env python3
"""
测试图片格式支持的脚本
验证各种MIME类型是否能正确映射到文件扩展名
"""

import sys
from Backend.artificial_intelligence.tools.storage import _mime_to_extension

sys.path.insert(0, "/home/beortust/MyData/CodeLib/CabbageEditor")


# 测试用例：(MIME类型, 期望的扩展名)
test_cases = [
    # 常见格式
    ("image/png", ".png"),
    ("image/jpeg", ".jpg"),
    ("image/jpg", ".jpg"),
    ("image/webp", ".webp"),
    ("image/gif", ".gif"),
    ("image/bmp", ".bmp"),
    ("image/x-bmp", ".bmp"),
    ("image/x-ms-bmp", ".bmp"),
    ("image/x-windows-bmp", ".bmp"),
    ("image/tiff", ".tiff"),
    ("image/x-tiff", ".tiff"),
    ("image/svg+xml", ".svg"),
    ("image/x-icon", ".ico"),
    ("image/vnd.microsoft.icon", ".ico"),
    ("image/x-jfif", ".jpg"),
    # 不常见格式（应该能处理）
    ("image/x-portable-bitmap", ".pbm"),
    ("image/x-portable-graymap", ".pgm"),
    ("image/x-portable-pixmap", ".ppm"),
    ("image/x-rgb", ".rgb"),
    ("image/x-xbitmap", ".xbm"),
    ("image/x-xpixmap", ".xpm"),
    # 大小写不敏感
    ("IMAGE/PNG", ".png"),
    ("Image/Jpeg", ".jpg"),
    # 带参数的MIME类型
    ("image/png; charset=utf-8", ".png"),
    ("image/jpeg; quality=0.8", ".jpg"),
    # 未知格式（应该返回.png作为默认值）
    ("image/unknown", ".unknown"),
    ("application/octet-stream", ".png"),
    ("text/plain", ".png"),
]


def test_mime_to_extension():
    print("=" * 70)
    print("测试图片格式支持")
    print("=" * 70)

    passed = 0
    failed = 0

    for mime_type, expected in test_cases:
        result = _mime_to_extension(mime_type)
        status = "✓ PASS" if result == expected else "✗ FAIL"

        if result == expected:
            passed += 1
            print(f"{status:8} | {mime_type:40} -> {result}")
        else:
            failed += 1
            print(f"{status:8} | {mime_type:40}")
            print(f"         Expected: {expected}, Got: {result}")

    print("=" * 70)
    print(f"总计：{passed} 通过, {failed} 失败")
    print("=" * 70)

    return failed == 0


if __name__ == "__main__":
    success = test_mime_to_extension()
    sys.exit(0 if success else 1)
