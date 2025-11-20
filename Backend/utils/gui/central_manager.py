import logging
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QPoint, QTimer
from PySide6.QtGui import QGuiApplication

logger = logging.getLogger(__name__)


def get_dock_area(position, float_position, size):
    position_map = {
        "left": (Qt.DockWidgetArea.LeftDockWidgetArea, False, None),
        "right": (Qt.DockWidgetArea.RightDockWidgetArea, False, None),
        "top": (Qt.DockWidgetArea.TopDockWidgetArea, False, None),
        "bottom": (Qt.DockWidgetArea.BottomDockWidgetArea, False, None),
    }

    if position.lower() == "float":
        screen = QGuiApplication.primaryScreen()
        float_position_map = {
            "top_left": (Qt.DockWidgetArea.AllDockWidgetAreas, True, screen.geometry().topLeft()),
            "bottom_left": (Qt.DockWidgetArea.AllDockWidgetAreas, True,
                            screen.geometry().bottomLeft() - QPoint(0, 200)),
            "top_right": (Qt.DockWidgetArea.AllDockWidgetAreas, True, screen.geometry().topRight() - QPoint(150, 0)),
            "bottom_right": (Qt.DockWidgetArea.AllDockWidgetAreas, True,
                             screen.geometry().bottomRight() - QPoint(150, 200)),
            "center": (
                Qt.DockWidgetArea.AllDockWidgetAreas,
                True,
                screen.geometry().center() - QPoint(int((size or {}).get("width", 600)) // 2,
                                                    int((size or {}).get("height", 320)) // 2),
            ),
        }
        return float_position_map.get(float_position.lower(),
                                      (Qt.DockWidgetArea.AllDockWidgetAreas, True, screen.geometry().topLeft()))

    return position_map.get(
        position.lower(), (Qt.DockWidgetArea.LeftDockWidgetArea, False, None)
    )


class CentralManager:
    def __init__(self, main_window=None):
        self.docks = {}
        self.main_window = main_window
        self._cleanup_widgets = []

    def set_main_window(self, main_window):
        """设置主窗口引用"""
        self.main_window = main_window

    def create_dock(self, route_name, route_path, position=None, float_position=None, size=None):
        """创建并注册 Dock"""
        if not route_name or not route_path:
            logger.error("route_name 和 route_path 不能为空")
            return None

        # 延迟导入避免循环依赖
        from Backend.window_layout.dock_widget import RouteDockWidget

        # 如果 Dock 已存在，先删除
        if self.docks.get(route_name):
            self.remove_dock(route_name)
            return None

        browser = None
        try:
            browser = QWebEngineView()
            browser.is_main_browser = False
            dock_area, isFloat, pos = get_dock_area(position or "left", float_position or "top_left", size)

            # 创建 Dock
            dock = RouteDockWidget(browser, route_name, route_path, self, self.main_window, isFloat)

            # 注册到管理器
            self.register_dock(route_name, dock)

            # 根据是否浮动进行不同处理
            if isFloat:
                if size:
                    dock.resize(size.get("width", 600), size.get("height", 400))
                    dock.browser.resize(size.get("width", 600), size.get("height", 400))
                dock.setWindowFlags(dock.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
                if pos:
                    dock.move(pos)
                dock.show()
            else:
                if self.main_window:
                    self.main_window.addDockWidget(dock_area, dock)

            logger.info(f"[CentralManager] 创建 Dock: {route_name}")
            return dock

        except Exception as e:
            logger.exception(f"[CentralManager] 创建 Dock 失败: {route_name}")
            if browser is not None:
                browser.deleteLater()
            return None

    def remove_dock(self, route_name):
        """删除并清理 Dock"""
        dock = self.docks.get(route_name)
        if not dock:
            logger.warning(f"[CentralManager] Dock 不存在: {route_name}")
            return False

        try:
            # 延迟导入避免循环依赖
            from Backend.window_layout.dock_widget import DockCleanupWidget  # noqa

            # 从主窗口移除
            if self.main_window:
                self.main_window.removeDockWidget(dock)

            # 获取 browser widget
            browser = dock.widget() if hasattr(dock, 'widget') else None

            # 创建清理器并保存引用
            cleanup = DockCleanupWidget(browser, route_name, self)
            self._cleanup_widgets.append(cleanup)

            # 200ms 后清理引用（足够完成3步清理）
            QTimer.singleShot(200, lambda: self._cleanup_widgets.remove(cleanup) if cleanup in self._cleanup_widgets else None)

            logger.info(f"[CentralManager] 删除 Dock: {route_name}")
            return True

        except Exception as e:
            logger.exception(f"[CentralManager] 删除 Dock 失败: {route_name}")
            return False

    def register_dock(self, route_name, dock):
        """注册 Dock 到管理器"""
        self.docks[route_name] = dock

    def delete_dock(self, route_name):
        """从管理器删除 Dock 引用"""
        if route_name in self.docks:
            del self.docks[route_name]

    def send_json_to_dock(self, route_name, json_data):
        """发送 JSON 数据到指定 Dock"""
        if route_name in self.docks:
            self.docks[route_name].send_message_to_dock(json_data)
        else:
            logger.warning(f"未找到路由 {route_name} 对应的 DockWidget")
