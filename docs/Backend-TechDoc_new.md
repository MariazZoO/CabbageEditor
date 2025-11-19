# CabbageEditor 后端技术文档（Refactor 版本）

> 本文描述 2025/11 架构重构后的 Backend。旧版文档参见 `Backend-TechDoc.md`，仅供 Legacy 参考。

## 1. 架构概览

```
┌────────────┐
│ Frontend   │  (QWebEngine + WebChannel)
└────┬───────┘
     │  WebChannel 信号/槽
┌────▼────────────┐
│ window_layout   │  (services/*.py + widgets)
└────┬────────────┘
     │  调用
┌────▼────────────┐
│ Core Services   │  (engine_core.services / artificial_intelligence.agent+api)
└────┬────────────┘
     │  依赖注入
┌────▼────────────┐
│ Engine Runtime  │  (engine_core bindings, SceneManager, CoronaEngine)
├────▼────────────┤
│ AI Layer        │  (LangChain agents, tools/, models/)
└─────────────────┘
```

- **配置 & 密钥**：`Backend/artificial_intelligence/config/config.py` 统一解析 `app_config.toml`，其中 `[secrets]` 保存凭据（默认示例见 `app_config.example.toml`）。
- **依赖注入**：`Backend/utils/bootstrap.py` 仅注册 `SceneManager` + Scene/Project Service；AI 相关逻辑改为在 `Backend/artificial_intelligence/agent` 内按需懒加载 LangChain Agent。
- **场景数据源**：所有 PySide 服务都通过同一个 `Backend.engine_core.scene_manager.SceneManager`，因此 RenderWidget、业务服务与 MCP 工具共享状态。

## 2. 目录结构要点

| 目录 | 说明 |
|------|------|
| Backend/artificial_intelligence/config/ | `config.py`（加载 `app_config.toml`）与 `app_config.example.toml`（示例配置、密钥模板） |
| Backend/shared/ | `container.py`（DI 容器）、`logging.py` 等基础设施 |
| Backend/engine_core/ | 引擎绑定（Scene/Actor/Camera/Light）、`scene_manager.py`、`services/`（scene/project） |
| Backend/artificial_intelligence/ | `config/llm_config.py`、`models/`、`tools/`（builtin / media / mcp）、`agent/`、`api/` |
| Backend/window_layout/ | PySide Qt 服务（`services/*.py`）、`widgets/`、`static_components.py`、文件对话框 |
| Backend/frontend_bridge/ | WebChannel 注册/清理、后续 JS Bridge 扩展点 |
| Backend/artificial_intelligence/tools/mcp | MCP 工具注册器（内置 scene_tools） |
| Backend/script/ | Blockly 运行时脚本输出目录 |
| docs/ | `backend_interface.md`（WebChannel 契约）、`Backend-TechDoc_new.md`（本文） |

## 3. 运行与配置

1. **前端**：构建 `Frontend/dist`。
2. **密钥**：复制 `Backend/artificial_intelligence/config/app_config.example.toml` 为 `app_config.toml`，在 `[secrets]` 中填入 `api_key` / `base_url`（也可通过 `~/.coronaengine/app_config.toml` 或环境变量覆盖）。
3. **后端**：`python Backend/main.py`。默认禁用 GPU，相关环境可在 `Backend/artificial_intelligence/config/app_config.toml` 的 `[runtime]` 部分配置。
4. **MCP/AI**：LangChain Agent 由 `Backend/artificial_intelligence/agent/create_default_agent()` 懒加载；默认会注册内置的 scene_tools，使 AI 直接操控当前进程中的 SceneManager，无需额外 MCP server。

## 4. 核心模块

### 4.1 SceneManager 与 SceneApplicationService

- `Backend/engine_core/scene_manager.py`：CoronaEngine 绑定的单例实现，内部复用 `Backend/engine_core/scene.py` 管理 Actor/Camera/Light。
- `SceneApplicationService`：
  - `create_scene(scene)`：复用 SceneManager，返回场景快照（name / sun_direction / actors / cameras / lights）。
  - `add_actor(scene, path)`：创建 `Backend.engine_core.actor.Actor`，同步触发 Qt 层 `actor_created`。
  - `set_camera`、`set_sun`：直接操作渲染用的 `Scene` 对象，避免重复计算导致“昼夜变换”抖动。
  - `export_scene(scene)`：调用 `_scene_snapshot` 返回 JSON。

### 4.2 Qt Service 层（`Backend/window_layout/services`）

| Service | 主要职责 |
|---------|----------|
| `AppService` | Dock/Route 创建、销毁、消息、命令分发。 |
| `SceneService` | 将 Qt Signal/Slot 绑定到 `SceneApplicationService`；`actor_operation` 结果通过 `scene_loaded` (type=actor_operation) 推送；`camera_move`/`sun_direction` 仅在失败时发出 `scene_error`。 |
| `ProjectService` | 文件对话框 + 场景服务；导入模型成功后调用 `sceneService.actor_created`，与旧行为一致。 |
| `ScriptingService` | Blockly 脚本写入 Backend/script/ + 生成 runScript.py。 |
| `AIService` | WorkerThread 包装 `Backend.artificial_intelligence.service.handle_user_message`，在后台线程执行 LangChain Agent 调用并格式化 JSON 响应。 |

WebChannel 注册流程详见 `Backend/frontend_bridge/webchannel.py`：
- 所有服务在 BrowserWidget 初始化时注册；
- `ProjectService` 现在接收同一个 `SceneService` 引用，便于复用信号；
- `SceneService`/`AIService` 等内部自动 bootstrap，无需外部注入。

### 4.3 AI / MCP

- `config/llm_config.py`：整合 env / user / defaults，与 `Backend/artificial_intelligence/config/secrets.py` 共用密钥文件，返回 `AIConfig`（包含 LLM、media 配置）。
- `models/`：目前仅实现 `client_openai.py`（`langchain_openai.ChatOpenAI`），后续可加其他 provider；入口 `models.get_chat_model(config)`。
- `tools/`：
  - `builtin/basic.py`：保底 `search`、`get_weather` 示例工具。
  - `media/`：`image_tools.py` / `video_tools.py` 预留 OpenAI Images、视频生成接口（默认返回占位字符串，flag 可在 config 中启用）。
  - `mcp/scene_tools.py`：提供 `scene_query` / `transform_model` 等 LangChain `StructuredTool`，可直接操控当前 SceneManager。
  - `mcp/registry.py`：引导 `scene_tools` 注入当前进程的 `SceneApplicationService`，不再依赖外部 MCP server。
- `agent/factory.py`：`create_default_agent()` → `langchain.agents.create_agent(model, tools, system_prompt)`，结果缓存为单例。
- `api/__init__.py`：暴露 `handle_user_message` / `invoke_messages`，内部维护最简单的多轮会话缓存，并将响应封装为 `{type:"ai_response", ...}` JSON 供 Qt 层复用。

## 5. 典型流程

### 5.1 导入模型
1. 前端调用 `projectService.open_file_dialog("MainScene", "model")`
2. `ProjectService` 打开文件 → 调用 `ProjectApplicationService.import_model`
3. Application 层通过 SceneService 添加 Actor → 返回 `{scene, actor:{name,path,type}}`
4. Qt 层发出 `scene_loaded` + `sceneService.actor_created`，前端 Scene 面板刷新。

### 5.2 昼夜变化按钮
1. 前端发送 `{sceneName, px,py,pz}` 给 `sceneService.sun_direction`
2. Application/service 直接调用 `Scene.set_sun_direction`；不再向前端回流新的朝向值，因此不会出现坐标抖动。
3. 若操作失败，`scene_error` 信号携带错误 JSON。

### 5.3 AI 对话
1. `aiService.send_message_to_ai` 收到 JSON `{message}`
2. WorkerThread 调用 `Backend.artificial_intelligence.service.handle_user_message`，内部会：
   - 将消息追加到内存中的会话历史；
   - 调用 LangChain Agent：`create_agent(...).invoke({"messages": history})`；
   - 自动挂载 MCP / media / builtin 工具。
3. 最终结果通过 `ai_response` 信号返回；异常（如 401）会被捕获并封装成 `{type:"error",content:"...",...}`。

## 6. WebChannel 契约

详见 `docs/backend_interface.md`，核心变化：
- `projectService.open_file_dialog` 在成功导入模型/多媒体后会额外触发 `sceneService.actor_created`。
- `sceneService.camera_move` / `sun_direction` 不再发 `scene_loaded`，仅在异常时通知。
- 所有 payload 均为 UTF-8 JSON 字符串，前端类型定义维护在 `Frontend/src/types/backend.ts`。

## 7. 故障排查

| 问题 | 排查提示 |
|------|----------|
| 导入模型无响应 | 检查 `sceneService.actor_created` 是否触发（可在控制台监听）；确认 SceneManager 已创建同名场景。 |
| 昼夜/相机抖动 | 确认前端只发送一次请求，无需等待回调；确保未复用旧接口。 |
| LLM 401 或工具异常 | 查看控制台 `AIService` 捕获的 JSON 错误；检查 `Backend/artificial_intelligence/config/app_config.toml` 中 `[secrets]` 的 `api_key` / `base_url`。 |
| WebChannel 未注册 | 确保 BrowserWidget 初始化完毕后调用 `setup_webchannel_for_view`；window 等待 `webChannelReady`。 |

## 8. 代码清理说明

重构后移除了以下旧文件/模块：
- 旧版 `Backend/application/*`、`Backend/core/*`、`Backend/infrastructure/*`、`Backend/interfaces/*` 均已拆分并合并进新的六大模块。
- 旧 `Backend/ui/*` 移动到 `Backend/window_layout/widgets/`，WebChannel 工具统一放在 `Backend/frontend_bridge/`。
- `Backend/LargeLanguageModel/*`：迁至 `experiments/llm_agents`，与运行时彻底解耦。

确保新提交中不再引用上述路径，避免 IDE 误导。

## 9. 版本记录

- **v2 (2025/11/10)**：全站架构重构、引入 DI + LLM/MCP 统一层、恢复 SceneManager、修复昼夜抖动。
- **v1 (Legacy)**：Bridge/Service 混合方案，详情见 `Backend-TechDoc.md`。

---
如需补充/修正，请在 PR 中同步更新本文件与 `backend_interface.md`，保持文档与实现一致。***
