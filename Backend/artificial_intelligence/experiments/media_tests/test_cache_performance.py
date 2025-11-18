"""
测试 MediaStore 缓存性能

对比使用缓存和不使用缓存时的性能差异
"""

import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import time
from Backend.artificial_intelligence.storage import get_media_store


def test_cache_performance():
    """测试缓存性能提升"""
    store = get_media_store()

    # 查找一个已存在的图片（从之前的测试生成的）
    test_url = "autosave://test_session/generated/generated/generated-4ae62c5ec918409cae1e0f83570062e0_0e5949d1.png"

    stored = store.resolve_url(test_url)
    if not stored:
        print("❌ 未找到测试图片，请先运行 image_generation_example.py")
        return

    print("=" * 60)
    print("MediaStore 缓存性能测试")
    print("=" * 60)
    print(f"\n测试图片: {stored.name}")
    print(f"文件大小: {stored.path.stat().st_size / 1024:.2f} KB\n")

    # 测试 1: 不使用缓存（每次都读取文件）
    print("【测试 1】不使用缓存（多次调用 stored.data_url）")
    print("-" * 60)
    start = time.time()
    for i in range(10):
        _ = stored.data_url  # 每次都重新读取文件
    elapsed_no_cache = time.time() - start
    print(f"10 次调用耗时: {elapsed_no_cache * 1000:.2f} ms")
    print(f"平均每次: {elapsed_no_cache * 100:.2f} ms\n")

    # 测试 2: 使用缓存
    print("【测试 2】使用缓存（多次调用 get_cached_data_url）")
    print("-" * 60)
    start = time.time()
    for i in range(10):
        _ = store.get_cached_data_url(stored)  # 第一次读取，后续使用缓存
    elapsed_with_cache = time.time() - start
    print(f"10 次调用耗时: {elapsed_with_cache * 1000:.2f} ms")
    print(f"平均每次: {elapsed_with_cache * 100:.2f} ms\n")

    # 性能提升
    speedup = (
        elapsed_no_cache / elapsed_with_cache
        if elapsed_with_cache > 0
        else float("inf")
    )
    print("=" * 60)
    print("性能对比")
    print("=" * 60)
    print(f"性能提升: {speedup:.2f}x")
    print(f"节省时间: {(elapsed_no_cache - elapsed_with_cache) * 1000:.2f} ms")
    print(f"效率提升: {((1 - elapsed_with_cache / elapsed_no_cache) * 100):.1f}%\n")

    # 测试 3: load_image_data_url 的缓存
    print("【测试 3】load_image_data_url 使用缓存")
    print("-" * 60)

    # 清除缓存
    store.clear_data_url_cache(stored)

    start = time.time()
    for i in range(10):
        _ = store.load_image_data_url(test_url, use_cache=True)
    elapsed_load_cached = time.time() - start
    print(f"10 次调用（use_cache=True）: {elapsed_load_cached * 1000:.2f} ms\n")

    # 清除缓存
    store.clear_data_url_cache(stored)

    start = time.time()
    for i in range(10):
        _ = store.load_image_data_url(test_url, use_cache=False)
    elapsed_load_no_cache = time.time() - start
    print(f"10 次调用（use_cache=False）: {elapsed_load_no_cache * 1000:.2f} ms")

    speedup2 = (
        elapsed_load_no_cache / elapsed_load_cached
        if elapsed_load_cached > 0
        else float("inf")
    )
    print(f"\n性能提升: {speedup2:.2f}x\n")

    # 缓存大小
    print("【缓存状态】")
    print("-" * 60)
    print(f"缓存条目数: {len(store._data_url_cache)}")
    cache_size = sum(len(v.encode("utf-8")) for v in store._data_url_cache.values())
    print(f"缓存占用: {cache_size / 1024:.2f} KB\n")

    print("✓ 缓存机制工作正常！")


if __name__ == "__main__":
    test_cache_performance()
