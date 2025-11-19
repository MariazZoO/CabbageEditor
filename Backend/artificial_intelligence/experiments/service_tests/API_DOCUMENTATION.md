# 媒体生成服务接口文档

本文档描述了所有媒体生成服务的统一接口规范。

## 目录
- [图像生成](#图像生成)
- [视频生成](#视频生成)
- [文案生成](#文案生成)
- [语音合成 (TTS)](#语音合成-tts)
- [音乐生成 (BGM)](#音乐生成-bgm)

---

## 图像生成

### 接口
`handle_image_generation(payload: dict) -> str`

### 请求参数
```python
{
    "prompt": "图像生成提示词",              # 必需
    "session_id": "session_xxx",            # 可选，用于会话管理
    "product_url": "data:image/...",        # 可选，产品图片（base64或URL）
    "scene_url": "data:image/..."           # 可选，场景图片（base64或URL）
}
```

### 响应示例
```json
{
    "type": "image_generation",
    "status": "success",
    "timestamp": 1700000000,
    "session_id": "session_xxx",
    "prompt": "生成的提示词",
    "image": {
        "name": "图像名称",
        "path": "本地路径",
        "url": "在线URL",
        "base64": "base64编码的图像数据"
    }
}
```

---

## 视频生成

### 接口
`handle_video_generation(payload: dict) -> str`

### 请求参数
```python
{
    "prompt": "视频生成提示词",              # 必需
    "image_url": "data:image/...",          # 必需，输入图片URL
    "session_id": "session_xxx",            # 可选
    "resolution": "720P",                   # 可选：480P/720P/1080P
    "prompt_extend": true                   # 可选：是否扩展提示词
}
```

### 响应示例
```json
{
    "type": "video_generation",
    "status": "success",
    "timestamp": 1700000000,
    "session_id": "session_xxx",
    "prompt": "实际使用的提示词",
    "source": "来源",
    "model": "模型名称",
    "video_url": "视频URL",
    "task_id": "任务ID",
    "resolution": "720P",
    "usage": {
        "video_duration": 5,
        "num_images": 1
    }
}
```

---

## 文案生成

### 接口
`handle_copywriting_generation(payload: dict) -> str`

### 请求参数

#### 产品文案
```python
{
    "type": "product",                      # 必需
    "product_name": "产品名称",              # 必需
    "product_features": "特点1,特点2",      # 必需
    "style": "专业",                        # 可选：专业、活泼、高端、亲切、幽默
    "length": "中等",                       # 可选：简短、中等、详细
    "session_id": "session_xxx"             # 可选
}
```

#### 营销文案
```python
{
    "type": "marketing",                    # 必需
    "theme": "营销主题",                     # 必需
    "target_audience": "目标受众",          # 必需
    "key_points": "要点1,要点2",            # 必需
    "platform": "通用",                     # 可选：通用、微信、微博、抖音、小红书
    "tone": "激励",                         # 可选：激励、温暖、紧迫、趣味
    "session_id": "session_xxx"             # 可选
}
```

#### 创意文案
```python
{
    "type": "creative",                     # 必需
    "content_type": "故事",                 # 必需：故事、诗歌、剧本等
    "theme": "创作主题",                     # 必需
    "keywords": "关键词1,关键词2",          # 可选
    "style": "现代",                        # 可选：现代、古典、浪漫、科技、悬疑等
    "length": "中等",                       # 可选：简短、中等、长篇
    "session_id": "session_xxx"             # 可选
}
```

### 响应示例
```json
{
    "type": "copywriting_generation",
    "copywriting_type": "product",
    "status": "success",
    "timestamp": 1700000000,
    "session_id": "session_xxx",
    "content": "生成的文案内容..."
}
```

---

## 语音合成 (TTS)

### 接口
`handle_tts_generation(payload: dict) -> str`

### 请求参数
```python
{
    "text": "待合成的文本内容",              # 必需
    "session_id": "session_xxx",            # 可选
    "voice_type": "zh_female_cancan_mars_bigtts",  # 可选，音色
    "speed_ratio": 1.0,                     # 可选，语速 [0.5, 2.0]
    "loudness_ratio": 1.0,                  # 可选，音量 [0.5, 2.0]
    "encoding": "mp3",                      # 可选，格式：mp3/wav/ogg_opus/pcm
    "rate": 24000,                          # 可选，采样率
    "max_wait_seconds": 60,                 # 可选，最大等待时间
    "poll_interval": 2.0                    # 可选，轮询间隔
}
```

### 响应示例
```json
{
    "type": "tts_generation",
    "status": "success",
    "timestamp": 1700000000,
    "session_id": "session_xxx",
    "task_id": "任务ID",
    "audio_url": "音频URL",
    "duration": 1000,
    "req_text_length": 10,
    "url_expire_time": 1700003600,
    "encoding": "mp3",
    "voice_type": "zh_female_cancan_mars_bigtts"
}
```

**注意**: 
- 音频URL有效期为1小时
- 异步模式，会自动轮询直到完成
- 最大文本长度：10万字符

---

## 音乐生成 (BGM)

### 接口
`handle_music_generation(payload: dict) -> str`

### 请求参数
```python
{
    "prompt": "音乐描述提示词",              # 必需
    "session_id": "session_xxx",            # 可选
    "style": "lofi",                        # 可选，音乐风格
    "model": "V5",                          # 可选，模型版本
    "duration": 20,                         # 可选，时长（秒）
    "wait": false,                          # 可选，是否等待完成
    "max_wait_seconds": 600,                # 可选，最大等待时间
    "poll_interval": 5.0                    # 可选，轮询间隔
}
```

### 响应示例

#### 快速模式 (wait=false)
```json
{
    "type": "music_generation",
    "status": "pending",
    "timestamp": 1700000000,
    "session_id": "session_xxx",
    "task_id": "任务ID",
    "model": "V5",
    "prompt": "音乐描述",
    "style": "lofi"
}
```

#### 同步模式 (wait=true)
```json
{
    "type": "music_generation",
    "status": "FIRST_SUCCESS",
    "timestamp": 1700000000,
    "session_id": "session_xxx",
    "task_id": "任务ID",
    "model": "V5",
    "prompt": "音乐描述",
    "style": "lofi",
    "audio_list": [
        {
            "index": 1,
            "id": "音频ID",
            "title": "音乐标题",
            "duration": 184.92,
            "audio_url": "音频URL",
            "image_url": "封面URL",
            "tags": "风格标签"
        }
    ],
    "audio_count": 1
}
```

---

## 统一错误响应

所有接口在出错时返回统一格式：

```json
{
    "type": "xxx_generation",
    "status": "error",
    "timestamp": 1700000000,
    "session_id": "session_xxx",
    "content": "错误信息描述"
}
```

---

## 调用示例

### Python
```python
from Backend.artificial_intelligence.service import (
    handle_image_generation,
    handle_video_generation,
    handle_copywriting_generation,
    handle_tts_generation,
    handle_music_generation,
)

# 图像生成
result = handle_image_generation({
    "prompt": "一只可爱的猫咪"
})

# 文案生成
result = handle_copywriting_generation({
    "type": "product",
    "product_name": "智能手表",
    "product_features": "防水,长续航"
})

# TTS生成
result = handle_tts_generation({
    "text": "你好世界"
})

# 音乐生成
result = handle_music_generation({
    "prompt": "轻松的钢琴曲",
    "wait": False
})
```

---

## 注意事项

1. **session_id**: 所有接口都支持可选的 `session_id` 参数，用于会话管理和历史记录
2. **异步处理**: TTS、视频、音乐生成都是异步的，会自动轮询直到完成
3. **URL过期**: TTS音频URL有效期1小时，需要及时使用或下载
4. **文件格式**: 
   - 图像：返回base64和URL
   - 视频：返回URL
   - TTS：返回URL
   - 音乐：返回URL列表
5. **配置要求**: 
   - 图像：需要配置灵雅AI
   - 视频：需要配置DashScope
   - 文案：需要配置豆包（doubao）
   - TTS：需要配置火山引擎
   - 音乐：需要配置Suno API
