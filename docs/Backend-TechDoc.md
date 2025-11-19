# CabbageEditor 后端技术文档

> ⚠️ 本文记录 Legacy 架构，所提的 `Backend/services/*`、`Backend/utils/*` 等路径已在新版中迁移至 `Backend/interfaces/qt/services` 与 `Backend/infrastructure/engine`。最新结构详见 `Backend-TechDoc_new.md`。

## 概述
后端基于 PySide6 的 Qt + QWebEngine 提供编辑器主程序与 Dock 容器，使用 Qt WebChannel 将 C++/Python 能力暴露给前端。当前采用“服务化 + 回调（无 Bridge 依赖）”设计：
- WebChannelHelper 统一注册与清理服务对象，并提供回调接线（on_create_route/on_remove_route/on_message_to_dock/on_command_to_main）
- BrowserWidget 是主 Web 容器，直接以回调方式接 AppService 信号，负责 Dock 的创建/销毁
- RouteDockWidget 是每个 Dock 的 Web 容器，注册自身 WebChannel，并将 AppService 的创建/删除请求“回流”至主窗口
- CentralManager 维护 Dock 注册表，并存放“创建/删除 Dock”的回调（由 BrowserWidget 注册），同时负责向指定 Dock 分发消息

目录涉及的关键模块：
- Backend/ui/browser_widget.py
- Backend/ui/dock_widget.py
- Backend/utils/webchannel_helper.py
- Backend/services/{app.py, scene.py, project.py, scripting.py, ai.py}
- Backend/utils/{central_manager.py, static_components.py}

## 运行时流程总览
1. 启动 main.py，创建主窗口并加载 Frontend/dist/index.html
2. BrowserWidget 调用 WebChannelHelper：注册各 Service，并将 AppService 的“创建/删除/消息/命令”信号直接回接到 BrowserWidget（AddDockWidget/RemoveDockWidget/消息转发/命令处理）
3. BrowserWidget 在初始化后向 CentralManager 注册“创建/删除 Dock”的回调（set_creator/set_remover）
4. 前端 new QWebChannel 后获得 window.appService/sceneService/...，发起业务调用
5. Dock 页面（RouteDockWidget）也注册自身 WebChannel：
   - on_create_route/on_remove_route 经 CentralManager 的回调“回流”到主窗口（或兜底调用 MainWindow.browser_widget）
   - on_message_to_dock 仅在 routename 命中当前 Dock 时转为本地 dock_event 处理

## WebChannel 与服务对象
WebChannel 暴露的对象（对象名 → 类）：
- appService → AppService
- sceneService → SceneService
- projectService → ProjectService
- scriptingService → ScriptingService
- aiService → AIService

说明：WebChannelHelper 内部维持一个 SceneManager 单例，服务信号不再桥接到 Bridge。Bridge 与 WebChannel 的路径解耦（当前实现不依赖 Bridge）。

### AppService（应用/窗口编排）
方法（Slot）：
- add_dock_widget(routename: str, routepath: str, position: str = "left", floatposition: str = "None", size: str|None)
- remove_dock_widget(routename: str)
- send_message_to_dock(routename: str, json_data: str)
- send_command_to_main(command_name: str, command_data: str)
- close_process()

信号（Signal）：
- create_route_requested(name, path, pos, floatpos, sizeObj)
- remove_route_requested(name)
- message_to_dock_requested(name, json)
- command_to_main_requested(name, data)

WebChannelHelper 回接：
- 主页面：create/remove → BrowserWidget.Add/RemoveDockWidget；message → CentralManager.send_json_to_dock；command → BrowserWidget.handle_command_to_main
- Dock 页面：create/remove → CentralManager 的回调（或兜底调用 MainWindow.browser_widget）；message → 仅当 routename 命中本 Dock 时交由本地处理

### SceneService（场景/Actor/相机/光源）
方法（Slot）：
- create_scene(data: str JSON {sceneName})
- create_actor(scene_name: str, obj_path: str)
- remove_actor(scene_name: str, actor_name: str)
- actor_operation(data: str JSON {sceneName, actorName, Operation, x,y,z})
- camera_move(data: str JSON {sceneName, position, forward, up, fov})
- sun_direction(data: str JSON {sceneName, px, py, pz})

信号（Signal）：
- actor_created(str JSON {name, path})
- scene_loaded(str JSON {actors: [{name,path}, ...]})
- scene_error(str JSON)

数据面向引擎的抽象在 Backend/utils/scene.py 内部通过 EngineObjectFactory 访问底层 C++ ECS（如可用），并保持 Python 端薄包装。

### ProjectService（项目/文件）
方法（Slot）：
- open_file_dialog(sceneName: str, file_type: str in {"model", "scene"})
- scene_save(data: str JSON)

信号（Signal）：
- scene_saved(str JSON {status, filepath})

### ScriptingService（运行脚本）
方法（Slot）：
- execute_python_code(code: str, index: int)

行为：
- 将传入代码写入 Backend/script/blockly_code.py
- 生成 Backend/runScript.py，按顺序 import 所有 blockly_code*.py 并调用其 run()
- 控制台打印：
  - [DEBUG] 脚本文件创建成功: ...
  - [DEBUG] runScript.py创建/覆盖成功: ...

### AIService（AI 对话）
方法（Slot）：
- send_message_to_ai(ai_message: str JSON {message})

信号（Signal）：
- ai_response(str JSON {type, content, status, timestamp})

内部使用 WorkerThread 线程执行 qa_one_sync 并回传结果。

## BrowserWidget（主容器）
职责：
- 作为主页面的 Web 容器，承载前端 Router 根页面
- 通过 WebChannelHelper 注册服务对象
- 以回调方式接 AppService 的 create/remove/message/command
- 在初始化后，将自身 Add/RemoveDockWidget 注册进 CentralManager（set_creator/set_remover）

AddDockWidget 逻辑：
- 根据 position/floatposition 选择 Dock 区域或浮动位置
- 复用 routename：若已存在则先删除后返回（实现“切换/关闭”行为）
- 为新 Dock 注入 window.__dockRouteName（供前端 useDragResize 识别目标）

## RouteDockWidget（Dock 容器）
职责：
- 承载对应路由页面（如 /Object、/SceneBar）
- 通过 WebChannelHelper 注册服务（Dock 页面也可直接调用服务）
- 处理来自前端的 Dock 事件（JSON 负载统一格式：{event: 'drag'|'float'|'resize'|'close', routename, ...}）
  - drag：deltaX/deltaY（仅浮动时移动）
  - float：isFloating（切换浮动）
  - resize：x/y/width/height（使用屏幕绝对坐标）
- Dock 内部创建/删除 Dock 的请求：on_create_route/on_remove_route → CentralManager 回调（或兜底调用 MainWindow.browser_widget.Add/RemoveDockWidget）
- 清理：注销 channel、回收 QWebEngineProfile/QWebEnginePage

## CentralManager（Dock 注册表）
- set_creator(fn)/set_remover(fn)：由 BrowserWidget 注册创建/删除 Dock 的回调
- create_route(name, path, pos, floatpos, size)：回调到注册的创建函数
- remove_route(name)：回调到注册的删除函数（若无则仅从注册表删除）
- register_dock(routename, dock)：登记 Dock 实例
- delete_dock(routename)：从注册表移除（不销毁 UI）
- send_json_to_dock(routename, json_data)：向目标 Dock 分发字符串消息（RouteDockWidget.send_message_to_dock → dock_event）

## 构建与运行
- Frontend 请先构建出 dist（Vite 构建），后端通过 static_components.url 指向 Frontend/dist/index.html
- 运行 Backend/main.py 即可（main.py 内默认启用软件渲染：QTWEBENGINE_DISABLE_GPU/Qt Quick software/OpenGL software）

## 事件/信号对照速查
- 主页面创建 Dock：appService.add_dock_widget → BrowserWidget.AddDockWidget → 创建 QDockWidget
- Dock 页面创建 Dock：appService.add_dock_widget（在 Dock 内）→ on_create_route → CentralManager.set_creator 回调 → BrowserWidget.AddDockWidget
- 向 Dock 发送消息：appService.send_message_to_dock →（主页面）CentralManager.send_json_to_dock → RouteDockWidget.send_message_to_dock → dock_event
- Scene 事件：sceneService.actor_created/scene_loaded → 前端 SceneBar 订阅更新 UI
- AI 响应：aiService.ai_response → RouteDockWidget 转为 window.receiveAIMessage 调 JS

## 约定与注意
- 前端所有 Service 调用须等待 window.webChannelReady
- add_dock_widget 的 size 参数推荐传 JSON 字符串（例如 {"width":520,"height":640}，AppService 会解析为对象）
- Dock 事件负载必须包含 routename（后端将校验并定向投递）
- WebChannel 路径不再依赖 Bridge；若项目仍保留 Bridge，其它非 WebChannel 逻辑可继续独立使用

## 故障排查
- QWebChannel 未初始化：检查 index.html 是否引入 qwebchannel.js（相对路径）、main.js 是否 new QWebChannel
- 无法创建 Dock：确认主页面已注册 CentralManager 回调；Dock 页面的 on_create_route 是否触发；routename 是否唯一
- 拖拽不动：检查 window.__dockRouteName 是否注入；前端 useDragResize 是否通过 appService 发送；Dock 是否处于浮动
- 前端无法连接服务：等待 webChannelReady；检查对象名 sceneService/appService 等是否存在

## 最近变更（要点）
- 移除 Bridge 依赖：WebChannel 不再经由 Bridge 转发信号，改为“服务化 + 回调”。
- WebChannelHelper：返回的 WebChannelContext 仅包含 channel 与 services；不再有 bridge 字段。
- AppService.add_dock_widget：最后一个参数改为兼容任意对象（object）；可传入 JSON 字符串或 JS 对象，后端都会解析为 dict 或 None。
- RouteDockWidget：在 setup_web_channel 中实现 on_create_route/on_remove_route 的“回流到主窗口”逻辑：
  - 优先调用 CentralManager._creator/_remover（由 BrowserWidget 注册）
  - 未注册则兜底调用 MainWindow.browser_widget.AddDockWidget/RemoveDockWidget
- AIService：内联最小 WorkerThread（QThread 包装），不再从 bridge 导入，避免删除 bridge.py 时服务初始化失败。

## Dock 创建 Dock 的数据流（回流链路）
1. Dock 页（JS）调用：`window.appService.add_dock_widget(name, path, pos, floatpos, size)`
2. AppService.add_dock_widget 解析 size 后发射：`create_route_requested(name, path, pos, floatpos, sizeObj)`
3. RouteDockWidget.setup_web_channel 中的 on_create_route 包装回调：
   - 调用 CentralManager._creator(name, path, pos, floatpos, sizeObj)
   - 若未注册，则兜底 MainWindow.browser_widget.AddDockWidget(...)
4. BrowserWidget.AddDockWidget 真正创建新的 RouteDockWidget 并显示

注：BrowserWidget.__init__ 在初始化时需注册全局回调：
- `central_manager.set_creator(self.AddDockWidget)`
- `central_manager.set_remover(self.RemoveDockWidget)`

## 快速校验（最小步骤）
- 主页面创建 Dock：
  - 前端（MainPage.vue）在 webChannelReady 后调用 `window.appService.add_dock_widget` → 观察 [DEBUG] AddDockWidget 日志。
- Dock 创建 Dock（例如 SceneBar → Object）：
  - Dock 控制台先打印 on_create_route，再打印主窗口 [DEBUG] AddDockWidget。
- 拖拽/缩放：
  - 前端 useDragResize 发送 `{event: 'drag'|'resize'|'float', routename, ...}` → RouteDockWidget.dock_event 生效。
