# 工具响应统一规范实现说明

## 设计原则

`interface_type` 由**调用层**决定，而非工具内部固定：
- **Agent 调用**：所有工具返回 `interface_type="integrated"`
- **独立接口调用**：各工具返回对应的类型（`image`、`speech`、`video`、`music`、`text`）

## 架构组件

### 1. 响应适配器 (`response_adapter.py`)

提供构建统一响应的核心函数：

```python
from Backend.artificial_intelligence.tools.response_adapter import (
    build_part,              # 构建单个 part
    ToolResult,              # 中间结果类（不含 interface_type）
    build_success_result,    # 构建成功结果
    build_error_result,      # 构建错误结果
    build_llm_tool_response, # 直接构建完整 envelope（独立接口用）
    build_error_response,    # 直接构建错误 envelope（独立接口用）
)
```

**核心类 `ToolResult`**：
- 工具内部返回的中间结构，不包含 `interface_type`
- 提供 `.to_envelope(interface_type)` 方法转换为最终 JSON
- 允许调用层灵活指定 `interface_type`

### 2. 工具实现模式

**图片生成工具示例**：
```python
def _generate(...) -> str:
    # 错误处理
    if error:
        return build_error_result(error_message="xxx").to_envelope(interface_type="image")
    
    # 成功构建 part
    part = build_part(
        content_type="image",
        content_text=prompt,
        content_url=image_url,
        parameter={"resolution": "1:1", ...}
    )
    
    # 返回成功结果（默认 interface_type="image"）
    return build_success_result(parts=[part], metadata={...}).to_envelope(interface_type="image")
```

**关键点**：
- 工具返回时硬编码 `interface_type="image"`（独立接口调用时的默认值）
- Agent 调用时会通过包装层修改为 `interface_type="integrated"`

### 3. Agent 包装层 (`agent_wrapper.py`)

将工具返回的 `interface_type` 统一修改为 `"integrated"`：

```python
from Backend.artificial_intelligence.tools.agent_wrapper import wrap_tools_for_agent

# 加载原始工具
raw_tools = load_tools(config)

# Agent 调用时包装
agent_tools = wrap_tools_for_agent(raw_tools)
```

**工作原理**：
1. 拦截工具调用
2. 解析返回的 JSON
3. 将 `llm_content[].interface_type` 改为 `"integrated"`
4. 返回修改后的 JSON

## 使用场景

### 场景 1：Agent 调用工具

```python
from Backend.artificial_intelligence.tools.base import load_tools
from Backend.artificial_intelligence.tools.agent_wrapper import wrap_tools_for_agent

# 加载工具
tools = load_tools(config)

# 包装给 Agent 使用
agent_tools = wrap_tools_for_agent(tools)

# Agent 执行
agent = create_react_agent(llm, agent_tools, prompt)
result = agent.invoke({"input": "生成一张猫的图片"})
```

**返回示例**（`interface_type="integrated"`）：
```json
{
  "session_id": "xxx",
  "error_code": 0,
  "status_info": "success",
  "llm_content": [
    {
      "role": "tools",
      "interface_type": "integrated",  // ← Agent 调用时统一为 integrated
      "sent_time_stamp": 1732199999999,
      "part": [
        {
          "content_type": "image",
          "content_text": "一只橘猫在阳光下",
          "content_url": "https://.../cat.png",
          "parameter": {"resolution": "1:1", "text_type": "image_generation"}
        }
      ]
    }
  ],
  "metadata": {"model": "xxx", "provider": "lingya"}
}
```

### 场景 2：独立接口调用

```python
from Backend.artificial_intelligence.tools.media.image_tools import load_image_tools

# 直接加载工具（不包装）
image_tools = load_image_tools(config)
generate_image = image_tools[0].func

# 直接调用
result = generate_image(prompt="一只橘猫", aspect_ratio="1:1")
```

**返回示例**（`interface_type="image"`）：
```json
{
  "session_id": "xxx",
  "error_code": 0,
  "status_info": "success",
  "llm_content": [
    {
      "role": "tools",
      "interface_type": "image",  // ← 独立接口保持原类型
      "sent_time_stamp": 1732199999999,
      "part": [
        {
          "content_type": "image",
          "content_text": "一只橘猫",
          "content_url": "https://.../cat.png",
          "parameter": {"resolution": "1:1", "text_type": "image_generation"}
        }
      ]
    }
  ],
  "metadata": {"model": "xxx", "provider": "lingya"}
}
```

## 响应结构规范

### 成功响应

```json
{
  "session_id": "String",
  "error_code": 0,
  "status_info": "success",
  "llm_content": [
    {
      "role": "tools",
      "interface_type": "integrated | image | video | speech | music | text",
      "sent_time_stamp": Number,
      "part": [
        {
          "content_type": "text | image | video | audio",
          "content_text": "可选：文本内容或提示词",
          "content_url": "可选：媒体URL或DataURI",
          "url_expire_time": Number,  // 可选：过期时间戳（毫秒）
          "parameter": {
            "resolution": "String",      // 图像、视频分辨率
            "duration": Number,          // 音频、视频时长（秒）
            "speech_type": "String",     // 语音音色类型
            "music_style": "String",     // 音乐风格
            "text_type": "String"        // 文案类型
          }
        }
      ]
    }
  ],
  "metadata": {
    // 工具特定的元数据（模型名、provider、任务ID等）
  }
}
```

### 错误响应

```json
{
  "session_id": "String",
  "error_code": 1,  // 非0表示错误
  "status_info": "错误描述信息",
  "llm_content": [
    {
      "role": "tools",
      "interface_type": "...",
      "sent_time_stamp": Number,
      "part": [
        {
          "content_type": "text",
          "content_text": "错误描述信息"
        }
      ]
    }
  ],
  "metadata": {}
}
```

## 工具改造步骤

### 步骤 1：导入适配器

```python
from Backend.artificial_intelligence.tools.response_adapter import (
    build_part,
    build_success_result,
    build_error_result,
)
```

### 步骤 2：改造错误处理

```python
# 旧代码
return json.dumps({"type": "xxx", "status": "error", "error": "..."})

# 新代码
return build_error_result(error_message="...").to_envelope(interface_type="xxx")
```

### 步骤 3：改造成功返回

```python
# 旧代码
return json.dumps({
    "type": "xxx",
    "status": "success",
    "data_url": "...",
    ...
})

# 新代码
part = build_part(
    content_type="image|video|audio|text",
    content_text="提示词或文本内容",
    content_url="媒体URL",
    parameter={...}
)
return build_success_result(
    parts=[part],
    metadata={...}
).to_envelope(interface_type="xxx")
```

## 前端解析示例

```javascript
function parseToolResponse(jsonStr) {
  const response = JSON.parse(jsonStr);
  
  // 检查错误
  if (response.error_code !== 0) {
    console.error(`工具错误: ${response.status_info}`);
    return null;
  }
  
  // 提取内容
  const content = response.llm_content[0];
  const interfaceType = content.interface_type;  // "integrated" or 具体类型
  const parts = content.part;
  
  // 处理各类内容
  parts.forEach(part => {
    const type = part.content_type;  // "text", "image", "video", "audio"
    const url = part.content_url;
    const text = part.content_text;
    const params = part.parameter || {};
    
    if (type === "image") {
      displayImage(url, text, params.resolution);
    } else if (type === "audio") {
      playAudio(url, params.duration, params.speech_type);
    }
    // ... 其他类型处理
  });
  
  return {
    interfaceType,
    parts,
    metadata: response.metadata
  };
}
```

## 后续改造计划

### 待改造工具列表

1. **视频生成** (`video_tools.py`)
   - `interface_type="video"`
   - `content_type="video"`
   - `parameter`: `resolution`, `duration`

2. **背景音乐** (`music_tools.py`)
   - `interface_type="music"`
   - 多音频返回多个 `part`
   - `parameter`: `music_style`, `duration`

3. **文案生成** (`text.py`)
   - `interface_type="text"`
   - `content_type="text"`
   - `parameter`: `text_type`（区分产品/营销/创意）

4. **场景查询** (`scene_tools.py`)
   - `interface_type="integrated"` 或 `"scene"`
   - `content_type="text"`
   - 结果列表放 `content_text`（JSON 字符串）

### 改造模板

```python
def _your_tool_function(...) -> str:
    """工具函数（遵循统一响应规范）"""
    from Backend.artificial_intelligence.tools.response_adapter import (
        build_part,
        build_success_result,
        build_error_result,
    )
    
    try:
        # 参数验证
        if invalid_input:
            return build_error_result(error_message="错误信息").to_envelope(interface_type="your_type")
        
        # 执行核心逻辑
        result = do_something()
        
        # 构建 part
        part = build_part(
            content_type="text|image|video|audio",
            content_text=...,
            content_url=...,
            url_expire_time=...,
            parameter={...}
        )
        
        # 返回成功结果
        return build_success_result(
            parts=[part],
            metadata={...}
        ).to_envelope(interface_type="your_type")
        
    except Exception as e:
        return build_error_result(error_message=str(e)).to_envelope(interface_type="your_type")
```

## 常见问题

### Q: 为什么工具内部要硬编码 interface_type？

A: 这是为了兼容独立接口调用。工具内部设置的是**默认类型**，Agent 调用时会通过包装层统一改为 `"integrated"`。

### Q: 如何在 Agent 和独立接口间共享工具？

A: 使用 `wrap_tools_for_agent()` 包装：
```python
# 独立接口
raw_tools = load_tools(config)
direct_call = raw_tools[0].func(...)  # interface_type="image"

# Agent 调用
agent_tools = wrap_tools_for_agent(raw_tools)
agent.invoke({"input": "..."})  # interface_type="integrated"
```

### Q: 多个 part 如何返回？

A: 构建 parts 列表：
```python
parts = [
    build_part(content_type="audio", content_url="url1", ...),
    build_part(content_type="audio", content_url="url2", ...),
]
return build_success_result(parts=parts, ...).to_envelope(interface_type="music")
```

### Q: 如何添加自定义元数据？

A: 在 `metadata` 参数中添加任意键值：
```python
return build_success_result(
    parts=[...],
    metadata={
        "model": "xxx",
        "provider": "yyy",
        "custom_field": "value"
    }
).to_envelope(interface_type="xxx")
```
