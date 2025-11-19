# CabbageEditor 前端技术文档（无 Bridge 版）

## 概述
前端基于 Vue 3 + Vite（Tailwind 用于样式），运行在 Qt 的 QWebEngineView 中。
通过 Qt WebChannel，后端将服务对象挂载到 window，供任意页面（包括 Dock 页面）直接调用。

暴露的服务对象（window.*）：
- appService：创建/删除 Dock、向 Dock 发送消息、向主窗口发命令
- sceneService：场景/Actor/相机/光源
- projectService：项目/文件导入与保存
- scriptingService：脚本生成与执行
- aiService：AI 对话

关键约定：
- 在调用任何服务前，必须等待 `window.webChannelReady`。
- 不再使用 pyBridge/bridge；所有交互统一通过服务对象进行。

```js
// 统一等待通道就绪
await (window.webChannelReady || Promise.resolve());
```

## 创建/删除 Dock（主页面或任何 Dock 页面）
- 创建：`window.appService.add_dock_widget(routename, routePath, position, floatposition, size)`
  - routename：唯一 ID，如 "SceneBar"、"Object_<name>"
  - routePath：形如 "/SceneBar?sceneName=scene1"、"/Object?sceneName=...&objectName=..."
  - position："left" | "right" | "top" | "bottom" | "float"
  - floatposition："top_left" | "top_right" | "bottom_left" | "bottom_right" | "center" | "None"
  - size：推荐 JSON 字符串或对象，例如 `{width: 520, height: 640}` 或 `JSON.stringify({width:520,height:640})`
- 删除：`window.appService.remove_dock_widget(routename)`

说明：
- 在主页面调用会直接命中主窗口的 `AddDockWidget/RemoveDockWidget`。
- 在 Dock 页面调用也可创建 Dock：后端会将创建/删除请求“回流”到主窗口，最终统一由主窗口创建或删除。

示例：
```js
await window.webChannelReady;
window.appService.add_dock_widget(
  "SceneBar",
  `/SceneBar?sceneName=${sceneName}`,
  "left",
  "None",
  { width: 520, height: 640 }
);
```

## Dock 拖拽/缩放（useDragResize）
- 事件统一发送到后端：`window.appService.send_message_to_dock(routename, jsonString)`
- 标准事件负载（JSON，对应 RouteDockWidget.dock_event）：
  - 通用字段：`{ event: 'drag'|'resize'|'float'|'close', routename }`
  - drag：`{ deltaX, deltaY }`（仅浮动时生效）
  - resize：`{ x, y, width, height }`（屏幕绝对坐标，处理上/左拉伸会移动+缩放）
  - float：`{ isFloating: true|false }`
- 节流建议：拖拽/缩放事件 20ms 发送一次；鼠标释放时补发一次“终态”。
- 后端会在 Dock 页加载完成后注入 `window.__dockRouteName = <routename>`，可用作目标路由名。

示例（伪代码）：
```js
const name = window.__dockRouteName;
// 拖拽中（节流）
window.appService.send_message_to_dock(
  name,
  JSON.stringify({ event: 'drag', routename: name, deltaX, deltaY })
);
// 切换浮动
window.appService.send_message_to_dock(
  name,
  JSON.stringify({ event: 'float', routename: name, isFloating: true })
);
```

## 场景相关（Scene/Actor/相机/光源）
- 创建场景：`window.sceneService.create_scene(JSON.stringify({ sceneName }))`
- 创建 Actor：`window.sceneService.create_actor(sceneName, objPath)`
- 删除 Actor：`window.sceneService.remove_actor(sceneName, actorName)`
- Actor 变换：`window.sceneService.actor_operation(JSON.stringify({ sceneName, actorName, Operation: 'Move'|'Rotate'|'Scale', x,y,z }))`
- 相机移动：`window.sceneService.camera_move(JSON.stringify({ sceneName, position, forward, up, fov }))`
- 太阳方向：`window.sceneService.sun_direction(JSON.stringify({ sceneName, px, py, pz }))`

订阅：
- `sceneService.actor_created` / `sceneService.scene_loaded`（通过 QWebChannel 信号 → Vue 里用 once/on 封装订阅，或在页面挂载时注册回调）

## 脚本与 AI
- 运行脚本：`window.scriptingService.execute_python_code(code, 0)`
- AI 对话：`window.aiService.send_message_to_ai(JSON.stringify({ message: '...' }))`
- AI 响应：后端会调用页面函数 `window.receiveAIMessage(data)`，需在对应 Dock 页里定义该函数以展示消息。

## 路由与资源
- 路由使用 Hash 模式；后端通过 `routePath` 的 fragment（hash）加载对应页面。
- index.html 引入 qwebchannel.js（相对路径），初始化完成后挂载 `window.webChannelReady`（Promise）。

最小初始化（概念示意）：
```html
<script src="./qwebchannel.js"></script>
<script>
  window.webChannelReady = new Promise((resolve) => {
    function boot() {
      if (typeof QWebChannel !== 'undefined' && typeof qt !== 'undefined' && qt.webChannelTransport) {
        new QWebChannel(qt.webChannelTransport, (channel) => {
          Object.assign(window, channel.objects); // 导出 appService/sceneService/...
          resolve();
        });
      } else {
        setTimeout(boot, 50);
      }
    }
    boot();
  });
</script>
```

## 实践建议
- routename 保持唯一，如 "Object_<scene>_<name>"，避免“同名即关闭”的行为误判为“没创建”。
- size 可传对象，后端会自动解析；若传字符串请用 JSON.stringify。
- useDragResize 统一封装 drag/resize/float/close 事件发送，保持节流与释放补发。
