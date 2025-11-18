# 媒体功能测试

本目录包含 AI 媒体生成功能的测试和示例代码。

## 测试文件

### 1. `image_generation_example.py`
图像生成功能测试，包括：
- 文生图（Text-to-Image）
- 图片编辑（Image-to-Image）
- 自动使用前一张图片作为输入

**运行方式：**
```bash
python Backend/artificial_intelligence/experiments/media_tests/image_generation_example.py
```

### 2. `video_generation_example.py`
视频生成功能测试（图生视频）

**运行方式：**
```bash
python Backend/artificial_intelligence/experiments/media_tests/video_generation_example.py
```

### 3. `test_cache_performance.py`
缓存性能测试，对比使用缓存和不使用缓存的性能差异

**运行方式：**
```bash
python Backend/artificial_intelligence/experiments/media_tests/test_cache_performance.py
```

## 配置要求

运行这些测试需要：
1. 配置好 AI 服务提供商的 API Key
2. 确保网络连接正常
3. 安装所有依赖包

## 测试结果

测试生成的图片和视频会保存在 `autosave/` 目录下，按 session_id 组织。
