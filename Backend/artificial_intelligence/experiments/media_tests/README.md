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

### 3. `music_generation_example.py`
音乐生成功能测试（Suno API），包括：
- 快速提交模式（立即返回任务ID）
- 同步等待模式（等待生成完成并下载）

**运行方式：**
```bash
# 需要先设置环境变量
export SUNO_API_KEY=你的密钥
python Backend/artificial_intelligence/experiments/media_tests/music_generation_example.py
```

### 4. `test_tts.py`
语音合成（TTS）工具测试

**运行方式：**
```bash
python Backend/artificial_intelligence/experiments/media_tests/test_tts.py
```

### 5. `test_cache_performance.py`
缓存性能测试，对比使用缓存和不使用缓存的性能差异

**运行方式：**
```bash
python Backend/artificial_intelligence/experiments/media_tests/test_cache_performance.py
```

## 配置要求

### 图像生成
在 `app_config.toml` 中配置：
```toml
[media.image]
enable = true
provider = "lingya"
model = "nano-banana"
```

### 视频生成
在 `app_config.toml` 中配置：
```toml
[media.video]
enable = true
provider = "dashscope"
model = "wan2.2-i2v-flash"
```

### 音乐生成
在 `app_config.toml` 中配置：
```toml
[music]
# Suno API 配置
api_key_env = "SUNO_API_KEY"
base_url = "https://api.sunoapi.org"
```
并设置环境变量：
```bash
export SUNO_API_KEY=你的密钥
```

### 语音合成（TTS）
在 `app_config.toml` 中配置：
```toml
[tts]
# 火山引擎 TTS 配置
appid = "你的AppID"
token = "你的Token"
# 可选：使用环境变量（更安全）
appid_env = "TTS_APPID"
token_env = "TTS_TOKEN"
```

## 测试结果

测试生成的媒体文件会保存在 `autosave/` 目录下，按 session_id 组织：
- 图片：`autosave/<session_id>/generated/images/`
- 视频：`autosave/<session_id>/generated/videos/`
- 音频：`autosave/<session_id>/generated/audio/`
- TTS 音频：当前目录下的 `audio_output.mp3`
