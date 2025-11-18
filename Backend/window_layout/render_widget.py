from PySide6.QtCore import QRect, Signal, Qt
from PySide6.QtWidgets import QWidget

from ..engine_core.entities.scene import Scene
from ..engine_core.entities.camera import Camera
from ..engine_core.entities.viewport import Viewport
from ..engine_core.managers.scene_manager import SceneManager

class RenderWidget(QWidget):
    geometry_changed = Signal(QRect)

    def __init__(self, Main_Window):
        super(RenderWidget, self).__init__()
        self.Main_Window = Main_Window

        self.setGeometry(0, 0, self.Main_Window.width(), self.Main_Window.height())
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #282C34;")

        # 使用 SceneManager 创建/获取场景
        self.scene_manager = SceneManager()  # 单例获取
        self.scene = self.scene_manager.create_scene("MainScene")

        # 创建相机并加入场景（OOP API）
        try:
            self.camera = Camera(
                position=[0.0, 0.0, 5.0],
                forward=[0.0, 0.0, 1.0],
                world_up=[0.0, -1.0, 0.0],
                fov=45.0,
                name="MainCamera"
            )

            # 设置渲染表面（在 Camera 上）
            try:
                self.camera.set_surface(int(self.winId()))
            except Exception as surf_err:
                print(f"[RenderWidget] Warning: Camera.set_surface failed: {surf_err}")

            # OOP: 通过 Viewport 绑定 Camera
            self.viewport = Viewport(self.width(), self.height())
            self.viewport.set_camera(self.camera)

            # 通过 Scene 包装器添加视口
            self.scene.add_viewport(self.viewport)
        except Exception as e:
            print(f"[RenderWidget] Failed to create or setup camera/viewport: {e}")
            self.camera = None
            self.viewport = None

    def get_scene(self) -> Scene:
        """返回当前渲染使用的场景对象"""
        return self.scene
