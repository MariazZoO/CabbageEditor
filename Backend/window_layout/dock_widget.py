import json
import logging

from PySide6.QtCore import Qt, QTimer, QObject, Slot, QPoint
from PySide6.QtGui import QColor, QCursor, QGuiApplication
from PySide6.QtWidgets import QDockWidget, QWidget
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineSettings
from Backend.frontend_bridge import setup_webchannel_for_view, teardown_webchannel_for_view

logger = logging.getLogger(__name__)


class DockDragBridge(QObject):
    """Expose minimal drag hooks for H5 to control float/move and trigger docking preview."""

    def __init__(self, dock_widget, main_window, parent=None):
        super(DockDragBridge, self).__init__(parent)
        self._dock = dock_widget
        self._main = main_window
        self._drag_start_global = None
        self._orig_dock_global = None
        # resize state
        self._resize_dir = None
        self._resize_start_mouse = None
        self._resize_start_geom = None
        self._NO_DOCK = getattr(Qt, 'NoDockWidgetArea', 0)

    @Slot(int, int)
    def start_drag(self, x, y):
        try:
            if not self._dock.isFloating():
                self._dock.setFloating(True)
                self._dock.raise_()
            # 显示/隐藏检测区域（当前实现始终隐藏，但调用不影响）
            if hasattr(self._main, 'show_detection_zones'):
                self._main.show_detection_zones(True)
            # 标记正在拖拽的 dock，供延迟停靠使用
            if hasattr(self._main, 'set_dragging_dock'):
                try:
                    self._main.set_dragging_dock(self._dock)
                except Exception:
                    pass
            web = self._dock.widget()
            web_global = web.mapToGlobal(QPoint(0, 0)) if web else self._dock.mapToGlobal(QPoint(0, 0))
            self._drag_start_global = web_global + QPoint(int(x), int(y))
            self._orig_dock_global = self._dock.mapToGlobal(QPoint(0, 0))
        except Exception:
            logger.exception("start_drag failed")

    @Slot(int, int)
    def drag_move(self, x, y):
        # 若已不再浮动（可能已在计时器触发时自动停靠），停止移动
        if not self._dock.isFloating():
            return
        if self._drag_start_global is None or self._orig_dock_global is None:
            return
        try:
            current_global = QCursor.pos()
            # 更新预览/计时（延迟停靠）
            area = self._NO_DOCK
            if hasattr(self._main, 'update_dock_preview'):
                area = self._main.update_dock_preview(current_global)
            # 无占位预览时，窗口跟随鼠标移动
            if area == self._NO_DOCK:
                delta = current_global - self._drag_start_global
                new_global = self._orig_dock_global + delta
                self._dock.move(new_global)
        except Exception:
            pass

    @Slot()
    def end_drag(self):
        try:
            # 释放时不再强制停靠（除非开启 _dock_on_release），仅做清理
            if hasattr(self._main, 'try_dock_widget') and self._drag_start_global is not None:
                try:
                    self._main.try_dock_widget(QCursor.pos(), self._dock)
                except TypeError:
                    self._main.try_dock_widget(QCursor.pos())
        except Exception:
            pass
        finally:
            if hasattr(self._main, 'show_detection_zones'):
                self._main.show_detection_zones(False)
            if hasattr(self._main, 'set_dragging_dock'):
                try:
                    self._main.set_dragging_dock(None)
                except Exception:
                    pass
            self._drag_start_global = None
            self._orig_dock_global = None

    # ---- Resize path via bridge ----
    @Slot(str, int, int)
    def start_resize(self, direction, x, y):
        try:
            if not self._dock.isFloating():
                self._dock.setFloating(True)
                self._dock.raise_()
            self._resize_dir = (direction or '').lower()
            self._resize_start_mouse = QCursor.pos()
            self._resize_start_geom = self._dock.frameGeometry()
        except Exception:
            self._resize_dir = None
            self._resize_start_mouse = None
            self._resize_start_geom = None

    @Slot(int, int)
    def resize_move(self, x, y):
        if not self._resize_dir or self._resize_start_mouse is None or self._resize_start_geom is None:
            return
        try:
            current = QCursor.pos()
            dx = current.x() - self._resize_start_mouse.x()
            dy = current.y() - self._resize_start_mouse.y()

            # starting geometry
            gx = self._resize_start_geom.x()
            gy = self._resize_start_geom.y()
            gw = self._resize_start_geom.width()
            gh = self._resize_start_geom.height()

            new_x, new_y, new_w, new_h = gx, gy, gw, gh
            d = self._resize_dir
            if 'n' in d:
                new_y = gy + dy
                new_h = gh - dy
            if 's' in d:
                new_h = gh + dy
            if 'w' in d:
                new_x = gx + dx
                new_w = gw - dx
            if 'e' in d:
                new_w = gw + dx

            # min constraints
            min_w, min_h = 200, 160
            if new_w < min_w:
                if 'w' in d:
                    # adjust x so right edge stays
                    new_x = new_x - (min_w - new_w)
                new_w = min_w
            if new_h < min_h:
                if 'n' in d:
                    new_y = new_y - (min_h - new_h)
                new_h = min_h

            # clamp to primary screen (basic)
            screen = QGuiApplication.primaryScreen().availableGeometry()
            # right/bottom clamp by shrinking if necessary
            if new_x < screen.left():
                if 'w' in d:
                    overflow = screen.left() - new_x
                    new_x = screen.left()
                    new_w = max(min_w, new_w - overflow)
                else:
                    new_x = screen.left()
            if new_y < screen.top():
                if 'n' in d:
                    overflow = screen.top() - new_y
                    new_y = screen.top()
                    new_h = max(min_h, new_h - overflow)
                else:
                    new_y = screen.top()
            if new_x + new_w > screen.right():
                # shrink width
                new_w = max(min_w, screen.right() - new_x)
            if new_y + new_h > screen.bottom():
                new_h = max(min_h, screen.bottom() - new_y)

            self._dock.setGeometry(new_x, new_y, new_w, new_h)
        except Exception:
            pass

    @Slot()
    def end_resize(self):
        self._resize_dir = None
        self._resize_start_mouse = None
        self._resize_start_geom = None


class RouteDockWidget(QDockWidget):
    def __init__(self, browser, name, path, CentralManager, Main_Window, isFloat):
        super(RouteDockWidget, self).__init__(name, Main_Window)
        self.round_corner_stylesheet = None
        self.page = None
        self.Main_Window = Main_Window
        self.max_width = int(Main_Window.width() * 0.3)
        self.min_height = int(Main_Window.height() * 0.5)
        self.browser = browser
        self.isFloat = isFloat
        self.central_manager = CentralManager
        self.name = name
        self.worker_threads = []
        self.profile = None
        self._webchannel_ctx = None
        self.services = {}

        from PySide6.QtCore import QUrl
        from Backend.utils import url as base_url
        self.url = QUrl(base_url.toString())
        self.url.setFragment(path)

        self.setup_ui()
        self.setup_web_channel()
        self.connect_signals()

        if isFloat:
            self.setFloating(True)
            self.show()

    def setup_ui(self):
        self.setMinimumSize(1, 1)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.update_stylesheet()
        self.setMaximumWidth(self.max_width)
        self.setMinimumHeight(self.min_height)
        self.setTitleBarWidget(QWidget())
        self.setContentsMargins(0, 0, 0, 0)

        self.browser.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.browser.setStyleSheet("background: transparent;")
        self.browser.page().setBackgroundColor(QColor(Qt.GlobalColor.transparent))
        self.browser.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        try:
            self.profile = QWebEngineProfile(self)

            try:

                if hasattr(self.profile, "setOffTheRecord"):
                    self.profile.setOffTheRecord(True)
                self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
                self.profile.setHttpCacheMaximumSize(0)
                self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)

                try:
                    settings = self.profile.settings()
                    settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
                except Exception:
                    pass
            except Exception:
                pass
            self.page = QWebEnginePage(self.profile, self.browser)
            self.browser.setPage(self.page)

            try:
                self.page.setBackgroundColor(QColor(Qt.GlobalColor.transparent))
            except Exception:
                pass
        except Exception:
            self.profile = None

        self.setWidget(self.browser)

    def update_stylesheet(self):
        self.round_corner_stylesheet = """
            QDockWidget {
                background: rgba(0, 0, 0, 0); 
                border: 8px solid rgba(100, 100, 100, 150);
                border-radius: 5px;
                padding: 4px;
            }
            QDockWidget[floating="true"] {
                border: 8px solid rgba(120, 120, 120, 200);
                padding: 4px;
            }
            QDockWidget::title {
                height: 0px;
            }
        """
        self.setStyleSheet(self.round_corner_stylesheet)

    def setup_web_channel(self):
        def _on_msg_to_dock(route_name, json_data):
            if route_name == self.name:
                self.send_message_to_dock(json_data)

        def _on_create_route(route_name, route_path, position, float_position, size):
            """创建新的 Dock - 直接调用 CentralManager"""
            try:
                if hasattr(self.central_manager, 'create_dock'):
                    self.central_manager.create_dock(route_name, route_path, position, float_position, size)
                else:
                    logger.error('CentralManager 没有 create_dock 方法')
            except Exception as e:
                logger.exception('_on_create_route 处理失败')

        def _on_remove_route(route_name):
            """删除 Dock - 直接调用 CentralManager"""
            try:
                if hasattr(self.central_manager, 'remove_dock'):
                    self.central_manager.remove_dock(route_name)
                else:
                    logger.error('CentralManager 没有 remove_dock 方法')
            except Exception as e:
                logger.exception('_on_remove_route 处理失败')

        host_window = getattr(self.Main_Window, 'osd', self.Main_Window)
        drag_bridge = DockDragBridge(self, host_window, self)

        self._webchannel_ctx = setup_webchannel_for_view(
            self.browser,
            self.central_manager,
            register_services=True,
            on_create_route=_on_create_route,
            on_remove_route=_on_remove_route,
            on_message_to_dock=_on_msg_to_dock,
            extra_objects={"dockBridge": drag_bridge}
        )
        self.services = getattr(self._webchannel_ctx, 'services', {}) or {}

        # 确保在设置 WebChannel 之后再加载页面，这样前端能拿到 dockBridge
        try:
            # 使用 SingleShotConnection 避免 lambda 捕获 self 导致内存泄漏
            self.browser.loadFinished.connect(
                lambda ok, name=self.name: self.browser.page().runJavaScript(
                    "window.__dockRouteName = {};".format(json.dumps(name))),
                Qt.ConnectionType.SingleShotConnection
            )
        except Exception:
            logger.exception('Failed to connect loadFinished')
        self.browser.load(self.url)

        self.central_manager.register_dock(self.name, self)

    def connect_signals(self):
        ai_service = self.services.get("aiService")
        if ai_service is not None:
            try:
                ai_service.ai_response.connect(self.send_ai_message_to_js)
            except Exception:
                logger.exception('Failed to connect ai_service response')

        self.topLevelChanged.connect(self.handle_top_level_change)
        self.destroyed.connect(self.cleanup_resources)

    def dock_event(self, event_type, event_data):
        try:
            data_obj = json.loads(event_data) if isinstance(event_data, str) else (event_data or {})
            inner_event = data_obj.get("event")
            if inner_event:
                event_type = inner_event
            target = data_obj.get("routename")
            if target is not None and target != self.name:
                return
        except Exception:
            return
        if event_type == "drag" and self.isFloating():
            try:
                data = data_obj if isinstance(data_obj, dict) else {}
                current_pos = self.pos()
                new_x = current_pos.x() + int(data.get("deltaX", 0))
                new_y = current_pos.y() + int(data.get("deltaY", 0))
                self.move(new_x, new_y)
            except Exception as e:
                logger.exception("处理拖拽事件失败")
        elif event_type == "close":
            self.close()
        elif event_type == "float":
            try:
                data = data_obj if isinstance(data_obj, dict) else {}
                self.setFloating(bool(data.get("isFloating", False)))
                self.raise_()
            except Exception as e:
                logger.exception("处理float事件失败")
        elif event_type == "resize":
            try:
                data = data_obj if isinstance(data_obj, dict) else {}
                x = int(data.get("x"))
                y = int(data.get("y"))
                width = int(data.get("width"))
                height = int(data.get("height"))

                self.move(x, y)
                self.resize(max(200, width), max(200, height))

            except Exception as e:
                logger.exception("处理resize事件失败")

    def handle_top_level_change(self):
        if self.isFloating():
            self.setStyleSheet(self.round_corner_stylesheet)
            features = self.features()
            features |= QDockWidget.DockWidgetFeature.DockWidgetFloatable
            features |= QDockWidget.DockWidgetFeature.DockWidgetMovable
            features |= QDockWidget.DockWidgetFeature.DockWidgetClosable
            self.setFeatures(features)
            self.setMaximumWidth(16777215)
            self.setMinimumHeight(1)
        else:
            self.setStyleSheet(self.round_corner_stylesheet)
            self.setMaximumWidth(self.max_width)
            self.setMinimumHeight(self.min_height)
            if hasattr(self, "browser"):
                self.browser.update()

    def send_message_to_dock(self, json_data):
        self.dock_event("dockData", json_data)

    def send_ai_message_to_js(self, message):
        try:
            if not isinstance(message, str):
                message = str(message)
            try:
                json.loads(message)
                js_code = "window.receiveAIMessage({})".format(message)
            except Exception:
                js_code = "window.receiveAIMessage({})".format(json.dumps({'content': message}))

            QTimer.singleShot(0, lambda: self.browser.page().runJavaScript(js_code))
        except Exception as e:
            logger.exception("发送消息到JS失败")

    def cleanup_resources(self):
        logger.info("[Dock清理] 开始清理: %s", self.name)

        try:
            # 断开信号连接，防止在清理过程中触发回调
            self._disconnect_signals()

            self._cleanup_webchannel()
            self._cleanup_web_page()
            self._cleanup_profile()
            self._cleanup_browser()
            self._unregister_from_manager()

            logger.info("[Dock清理] 完成清理: %s", self.name)
        except Exception as e:
            logger.exception("[Dock清理] 异常: %s", self.name)

    def _disconnect_signals(self):
        """断开所有信号连接，防止清理过程中的回调"""
        try:
            # 断开 aiService 的信号
            ai_service = self.services.get("aiService")
            if ai_service is not None:
                try:
                    ai_service.ai_response.disconnect(self.send_ai_message_to_js)
                    logger.debug("[Dock清理] 已断开 aiService 信号")
                except (RuntimeError, TypeError):
                    pass
        except Exception:
            pass

        try:
            # 断开 topLevelChanged 信号
            self.topLevelChanged.disconnect(self.handle_top_level_change)
            logger.debug("[Dock清理] 已断开 topLevelChanged 信号")
        except (RuntimeError, TypeError):
            pass

    def _cleanup_webchannel(self):
        """清理 WebChannel 连接"""
        if getattr(self, "_webchannel_ctx", None):
            try:
                teardown_webchannel_for_view(self.browser, self._webchannel_ctx)
                self._webchannel_ctx = None
                logger.info("[Dock清理] WebChannel 已释放")
            except Exception as e:
                logger.exception("[Dock清理] WebChannel 释放失败")

    def _cleanup_web_page(self):
        """清理 Web 页面：断开引用并标记删除，同时保存正在删除的 page 对象供后续检查"""
        if hasattr(self, "page") and self.page:
            try:
                page_obj = self.page
                # 断开 page 与父对象关系并标记删除
                try:
                    page_obj.setParent(None)
                except Exception:
                    pass
                try:
                    page_obj.deleteLater()
                except Exception:
                    pass

                # 保留对正在删除 page 的引用，供 later 检测/连接使用
                self._page_being_deleted = page_obj
                self.page = None
                logger.info("[Dock清理] Web页面已标记删除")
            except Exception as e:
                logger.exception("[Dock清理] Web页面释放失败")

    def _cleanup_profile(self):
        """清理 WebEngine Profile：在关联的 Page 完全销毁后再删除 Profile"""
        if getattr(self, "profile", None) is not None:
            try:
                try:
                    self.profile.clearHttpCache()
                except Exception:
                    pass

                profile_to_delete = self.profile
                self.profile = None

                # 如果我们知道有一个正在被删除的 page，等它 destroyed 信号后再删除 profile
                page_obj = getattr(self, '_page_being_deleted', None)
                if page_obj is not None:
                    try:
                        def _delete_profile_after_page(_=None, p=profile_to_delete):
                            try:
                                p.deleteLater()
                                logger.info("[Dock清理] Profile 已在 page 销毁后删除")
                            except Exception as e:
                                logger.exception("[Dock清理] Profile 删除失败")

                        # Connect the destroyed signal. If the object is already scheduled for deletion,
                        # destroyed will still be emitted and our slot will run.
                        page_obj.destroyed.connect(_delete_profile_after_page)
                        logger.info("[Dock清理] Profile 的删除已绑定到 page.destroyed 信号")

                        # 保留弱引用说明：一旦处理完可以移除引用
                        QTimer.singleShot(500, lambda: setattr(self, '_page_being_deleted', None))
                    except Exception as e:
                        # Fallback: delete profile after a short timeout
                        logger.exception("[Dock清理] 无法绑定 destroyed 信号，改用延迟删除")
                        QTimer.singleShot(100, lambda p=profile_to_delete: (p.deleteLater(), logger.info("[Dock清理] Profile 已延迟删除")))
                else:
                    # 没有 page 在删除，直接删除 profile
                    try:
                        profile_to_delete.deleteLater()
                        logger.info("[Dock清理] Profile 已删除")
                    except Exception as e:
                        logger.exception("[Dock清理] Profile 删除失败")

                logger.info("[Dock清理] Profile 已安排删除流程")
            except Exception as e:
                logger.exception("[Dock清理] Profile 释放失败")

    def _cleanup_browser(self):
        """清理浏览器 Widget"""
        if hasattr(self, "browser") and self.browser:
            try:
                # 先断开浏览器的 Page 引用
                try:
                    self.browser.setPage(None)
                except Exception:
                    pass

                self.browser.deleteLater()
                logger.info("[Dock清理] 浏览器已标记删除")
            except Exception as e:
                logger.exception("[Dock清理] 浏览器释放失败")

    def _unregister_from_manager(self):
        """从管理器注销"""
        try:
            if hasattr(self, "central_manager") and self.central_manager:
                self.central_manager.delete_dock(self.name)
                logger.info("[Dock清理] 已从管理器注销")
        except Exception as e:
            logger.exception("[Dock清理] 注销失败")

    def closeEvent(self, event):
        """关闭事件处理 - 清理工作线程"""
        logger.info("[Dock关闭] 触发关闭事件: %s", self.name)

        try:
            self._stop_worker_threads()
        except Exception as e:
            logger.exception("[Dock关闭] 线程清理异常: %s", self.name)

        # 调用父类的关闭事件
        super(RouteDockWidget, self).closeEvent(event)

    def _stop_worker_threads(self):
        """停止所有工作线程"""
        if not hasattr(self, 'worker_threads') or not self.worker_threads:
            return

        logger.info("[Dock关闭] 停止 %d 个工作线程", len(self.worker_threads))

        for thread in self.worker_threads:
            try:
                thread.quit()
                thread.wait()
            except Exception as e:
                logger.exception("[Dock关闭] 线程停止失败")

        self.worker_threads.clear()


class DockCleanupWidget(QWidget):
    CLEANUP_DELAY = 50
    def __init__(self, browser, name, central_manager):
        super(DockCleanupWidget, self).__init__()
        self.central_manager = central_manager
        self.browser = browser
        self.dock_name = name
        self.dock = self.central_manager.docks.get(name)

        if self.dock:
            logger.info("[Dock清理器] 开始清理: %s", name)
            self._start_cleanup()
        else:
            logger.info("[Dock清理器] Dock 不存在: %s", name)

    def _start_cleanup(self):
        """启动清理流程"""
        self.dock.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        QTimer.singleShot(0, self._cleanup_content)

    def _cleanup_content(self):
        """步骤1: 清理 Dock 内容"""
        logger.info("[Dock清理器] [步骤1/3] 开始清理内容: %s", self.dock_name)

        try:
            if not self._is_dock_valid():
                logger.info("[Dock清理器] [步骤1/3] Dock 已失效，跳过内容清理: %s", self.dock_name)
                QTimer.singleShot(self.CLEANUP_DELAY, self._cleanup_dock_widget)
                return

            content = self.dock.widget()
            if content:
                logger.info("[Dock清理器] [步骤1/3] 清理内容 Widget: %s", self.dock_name)
                content.hide()

                # 清理 WebChannel
                try:
                    if hasattr(content, 'page') and content.page():
                        content.page().setWebChannel(None)
                        logger.info("[Dock清理器] [步骤1/3] WebChannel 已清理: %s", self.dock_name)
                except RuntimeError:
                    pass

                content.setParent(None)
                logger.info("[Dock清理器] [步骤1/3] 内容 Widget 已移除: %s", self.dock_name)
            else:
                logger.info("[Dock清理器] [步骤1/3] 无内容 Widget: %s", self.dock_name)
        except Exception as e:
            logger.exception("[Dock清理器] [步骤1/3] 内容清理失败: %s", self.dock_name)

        # 继续下一步
        logger.info("[Dock清理器] [步骤1/3] 完成，等待 %dms 后进入步骤2: %s", self.CLEANUP_DELAY, self.dock_name)
        QTimer.singleShot(self.CLEANUP_DELAY, self._cleanup_dock_widget)

    def _cleanup_dock_widget(self):
        """步骤2: 清理 Dock 本身"""
        logger.info("[Dock清理器] [步骤2/3] 开始清理 Dock Widget: %s", self.dock_name)

        try:
            if self._is_dock_valid():
                if self.dock.isVisible():
                    logger.info("[Dock清理器] [步骤2/3] 隐藏并删除 Dock: %s", self.dock_name)
                    self.dock.hide()
                    self.dock.setParent(None)
                    self.dock.deleteLater()
                    logger.info("[Dock清理器] [步骤2/3] Dock 已标记删除: %s", self.dock_name)
                else:
                    logger.info("[Dock清理器] [步骤2/3] Dock 已隐藏，仅删除: %s", self.dock_name)
                    self.dock.setParent(None)
                    self.dock.deleteLater()
            else:
                logger.info("[Dock清理器] [步骤2/3] Dock 已失效: %s", self.dock_name)
        except RuntimeError as e:
            logger.exception("[Dock清理器] [步骤2/3] Dock 已提前删除")
        except Exception as e:
            logger.exception("[Dock清理器] [步骤2/3] Dock 删除失败: %s", self.dock_name)

        # 从管理器移除
        self._unregister_dock()

        # 继续下一步
        logger.info("[Dock清理器] [步骤2/3] 完成，等待 %dms 后进入步骤3: %s", self.CLEANUP_DELAY, self.dock_name)
        QTimer.singleShot(self.CLEANUP_DELAY, self._finalize_cleanup)

    def _unregister_dock(self):
        """从管理器注销 Dock"""
        try:
            if self.dock_name in self.central_manager.docks:
                del self.central_manager.docks[self.dock_name]
                logger.info("[Dock清理器] 已从管理器注销: %s", self.dock_name)
        except Exception as e:
            logger.exception("[Dock清理器] 注销失败: %s", self.dock_name)

    def _finalize_cleanup(self):
        """步骤3: 最终确认"""
        logger.info("[Dock清理器] [步骤3/3] 最终清理: %s", self.dock_name)

        # 清理自身引用
        self.dock = None
        self.central_manager = None
        self.browser = None

        logger.info("[Dock清理器] [步骤3/3] 完成所有清理: %s", self.dock_name)

    def _is_dock_valid(self):
        """检查 Dock 是否仍然有效"""
        return self.dock is not None and self.dock.isWidgetType()
