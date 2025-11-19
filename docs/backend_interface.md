## Frontend ↔ Backend Contract (Refactored)

| Service          | Entry (WebChannel) | Method/Signal                      | Payload (JSON)                                                    | Notes |
|------------------|--------------------|------------------------------------|-------------------------------------------------------------------|-------|
| `appService`     | `send_command_to_main` | `{ "command": "go_home" }` etc.  | Routed to `BrowserWidget.handle_command_to_main`.                 | Unchanged. |
| `sceneService`   | Slot `create_scene(data)` | `{ "sceneName": "MainScene" }` | Creates/returns snapshot via `scene_loaded` signal.               | Backed by `SceneApplicationService`. |
|                  | Slot `create_actor(scene, path)` | plain args | Emits `actor_created` after `SceneApplicationService.add_actor`. | |
|                  | Slot `actor_operation(payload)` | `{ sceneName, actorName, Operation, x, y, z }` | Applies transform, emits `actor_created` event with delta. | |
|                  | Slot `camera_move(payload)` | `{ sceneName, position, forward, up, fov }` | Updates camera姿态；无直接回调，仅错误时触发 `scene_error`. | |
|                  | Slot `sun_direction(payload)` | `{ sceneName, px, py, pz }` | 更新太阳方向；无直接回调，仅错误时触发 `scene_error`. | |
| `projectService` | Slot `open_file_dialog(scene, type)` | `type` in `model/scene/multimedia` | Wraps file dialog + `SceneApplicationService`; 成功导入模型会额外触发 `sceneService.actor_created`. | |
|                  | Slot `scene_save(data)` | Scene JSON | Emits `scene_saved` with status + `filepath`. | |
| `scriptingService` | Slot `execute_python_code(code, index)` | raw python, index | Writes to `Backend/script`, regenerates `runScript.py`. | Path derived from `Settings.paths.script_dir`. |
| `aiService`      | Slot `send_message_to_ai(payload)` | `{ "message": "<text>" }` | 调用 `Backend.artificial_intelligence.service.handle_user_message`，返回 LangChain Agent 响应。 | Agent 基于 `create_agent(model, tools)`，工具来自 MCP / media / builtin。 |

Signals:  
`actor_created`, `scene_loaded`, `scene_saved`, `script_error`, `ai_response`, `create_route_requested`, `remove_route_requested`, `message_to_dock_requested`, `command_to_main_requested`.

All payloads are UTF-8 JSON strings. Schema definitions live in `Frontend/src/types/backend.ts`.

### Secret & Config Management
- 复制 `Backend/artificial_intelligence/config/app_config.example.toml` 为 `app_config.toml`，在 `[secrets]` 段中写入 `api_key` / `base_url`，并按需调整 `[llm]`、`[mcp]`。
- 也可以在 `~/.coronaengine/app_config.toml` 中覆盖同名字段；环境变量（如 `CORONA_API_KEY`、`CORONA_LLM_MODEL`）拥有最高优先级。

### Service Composition
```
Frontend (WebChannel)
   -> `window_layout.services.*` (`sceneService`, `projectService`, `aiService`, ...)
       -> Core services (`engine_core.services.*`) / LangChain Agent (`artificial_intelligence.agent + service`)
           -> Engine runtime (`engine_core` bindings) / AI adapters (`langchain` agents + MCP 工具)
```

Use `Backend/tools/bootstrap.py` to register new services before touching Qt/UI.
