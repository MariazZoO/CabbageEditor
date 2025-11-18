from __future__ import annotations
import typing as _t
import logging
import weakref
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView


logger = logging.getLogger(__name__)


class WebChannelContext:
    def __init__(self, channel: QWebChannel, services=None) -> None:
        self.channel = channel
        self.services = services or {}


def setup_webchannel_for_view(
    view: QWebEngineView,
    central_manager,
    *,
    register_services: bool = False,
    on_create_route: _t.Callable | None = None,
    on_remove_route: _t.Callable | None = None,
    on_message_to_dock: _t.Callable[[str, str], None] | None = None,
    on_command_to_main: _t.Callable[[str, str], None] | None = None,
    extra_objects=None,
) -> WebChannelContext:
    channel = QWebChannel()

    services = {}

    if register_services:
        try:
            from Backend.frontend_bridge import (
                SceneService,
                AIService,
                ImageGenerationService,
                ScriptingService,
                ProjectService,
                AppService,
            )
            scene_service = SceneService(None)
            ai_service = AIService(None)
            image_gen_service = ImageGenerationService(None)
            scripting_service = ScriptingService(None)
            project_service = ProjectService(scene_service, None)
            app_service = AppService(None)

            channel.registerObject("sceneService", scene_service)
            channel.registerObject("aiService", ai_service)
            channel.registerObject("imageGenerationService", image_gen_service)
            channel.registerObject("scriptingService", scripting_service)
            channel.registerObject("projectService", project_service)
            channel.registerObject("appService", app_service)

            # AppService -> UI 回调（优先使用传入回调，其次尝试 central_manager）
            if on_create_route is not None:
                app_service.create_route_requested.connect(on_create_route)
            if on_remove_route is not None:
                app_service.remove_route_requested.connect(on_remove_route)
            if on_message_to_dock is not None:
                app_service.message_to_dock_requested.connect(on_message_to_dock)
            elif central_manager is not None and hasattr(central_manager, 'send_json_to_dock'):
                # 使用弱引用避免 lambda 捕获 central_manager 导致引用泄漏
                cm_ref = weakref.ref(central_manager)

                def _send_to_dock(name, data, cm_ref=cm_ref):
                    cm = cm_ref()
                    if cm is not None:
                        cm.send_json_to_dock(name, data)

                app_service.message_to_dock_requested.connect(_send_to_dock)
            if on_command_to_main is not None:
                app_service.command_to_main_requested.connect(on_command_to_main)

            services = {
                "sceneService": scene_service,
                "aiService": ai_service,
                "imageGenerationService": image_gen_service,
                "scriptingService": scripting_service,
                "projectService": project_service,
                "appService": app_service,
            }
        except Exception as e:
            logger.exception("注册服务对象失败: %s", e)

    # 注册自定义对象（如 DockBridge）
    if extra_objects:
        for name, obj in extra_objects.items():
            try:
                channel.registerObject(name, obj)
            except Exception as e:
                logger.exception("注册自定义对象 %s 失败: %s", name, e)

    try:
        view.page().setWebChannel(channel)
    except Exception:
        pass

    return WebChannelContext(channel=channel, services=services)


def teardown_webchannel_for_view(view: QWebEngineView, ctx: WebChannelContext) -> None:
    """解除绑定和清理：注销所有注册到 channel 的服务。"""
    try:
        if ctx and ctx.services:
            # 清理 AIService 的工作线程
            ai_service = ctx.services.get('aiService')
            if ai_service and hasattr(ai_service, 'cleanup'):
                try:
                    ai_service.cleanup()
                except Exception:
                    logger.exception("清理 AIService 失败")

            # 清理 ImageGenerationService 的工作线程
            image_gen_service = ctx.services.get('imageGenerationService')
            if image_gen_service and hasattr(image_gen_service, 'cleanup'):
                try:
                    image_gen_service.cleanup()
                except Exception:
                    logger.exception("清理 ImageGenerationService 失败")

            # 断开 AppService 的信号连接
            app_service = ctx.services.get('appService')
            if app_service:
                try:
                    app_service.create_route_requested.disconnect()
                    app_service.remove_route_requested.disconnect()
                    app_service.message_to_dock_requested.disconnect()
                    app_service.command_to_main_requested.disconnect()
                except (RuntimeError, TypeError):
                    pass

            # 注销所有对象
            if ctx.channel:
                for obj in ctx.services.values():
                    try:
                        ctx.channel.deregisterObject(obj)
                    except Exception:
                        pass
    except Exception:
        pass

    try:
        if ctx and ctx.channel:
            ctx.channel.deleteLater()
    except Exception:
        pass
