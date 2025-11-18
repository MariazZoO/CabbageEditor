from typing import Any, Dict, Optional

from ..engine_import import load_corona_engine

CoronaEngine = load_corona_engine()


class Viewport:
    """
    Viewport 包装类：视口管理，绑定 Camera 和 ImageEffects

    使用方式：
        viewport = Viewport(1920, 1080)
        viewport.set_camera(camera)
        scene.add_viewport(viewport)
    """

    def __init__(self, width: int = 1920, height: int = 1080, light_field: bool = False, name: str = "Viewport"):
        """
        创建 Viewport 对象

        Args:
            width: 视口宽度
            height: 视口高度
            light_field: 是否使用光场
            name: 视口名称
        """
        if CoronaEngine is None:
            raise RuntimeError("CoronaEngine 未初始化")

        ViewportCtor = getattr(CoronaEngine, 'Viewport', None)
        if ViewportCtor is None:
            raise RuntimeError("CoronaEngine 未提供 Viewport 构造器")

        self.engine_obj = ViewportCtor(width, height, light_field)
        self.name = name
        self.width = width
        self.height = height

    def set_camera(self, camera: Any):
        """设置相机（接受 Camera 包装器或原始引擎对象）"""
        try:
            cam_obj = camera.engine_obj if hasattr(camera, 'engine_obj') else camera
            self.engine_obj.set_camera(cam_obj)
        except Exception as e:
            raise RuntimeError(f"Viewport.set_camera 失败: {e}") from e

    def get_camera(self) -> Optional[Any]:
        """获取相机（返回原始引擎对象）"""
        try:
            return self.engine_obj.get_camera()
        except Exception as e:
            raise RuntimeError(f"Viewport.get_camera 失败: {e}") from e

    def has_camera(self) -> bool:
        """检查是否有相机"""
        try:
            return self.engine_obj.has_camera()
        except Exception as e:
            raise RuntimeError(f"Viewport.has_camera 失败: {e}") from e

    def remove_camera(self):
        """移除相机"""
        try:
            self.engine_obj.remove_camera()
        except Exception as e:
            raise RuntimeError(f"Viewport.remove_camera 失败: {e}") from e

    def set_image_effects(self, effects: Any):
        """设置图像效果"""
        try:
            fx_obj = effects.engine_obj if hasattr(effects, 'engine_obj') else effects
            self.engine_obj.set_image_effects(fx_obj)
        except Exception as e:
            raise RuntimeError(f"Viewport.set_image_effects 失败: {e}") from e

    def get_image_effects(self) -> Optional[Any]:
        """获取图像效果"""
        try:
            return self.engine_obj.get_image_effects()
        except Exception as e:
            raise RuntimeError(f"Viewport.get_image_effects 失败: {e}") from e

    def has_image_effects(self) -> bool:
        """检查是否有图像效果"""
        try:
            return self.engine_obj.has_image_effects()
        except Exception as e:
            raise RuntimeError(f"Viewport.has_image_effects 失败: {e}") from e

    def remove_image_effects(self):
        """移除图像效果"""
        try:
            self.engine_obj.remove_image_effects()
        except Exception as e:
            raise RuntimeError(f"Viewport.remove_image_effects 失败: {e}") from e

    def set_size(self, width: int, height: int):
        """设置视口尺寸"""
        try:
            self.width = width
            self.height = height
            self.engine_obj.set_size(width, height)
        except Exception as e:
            raise RuntimeError(f"Viewport.set_size 失败: {e}") from e

    def set_viewport_rect(self, x: int, y: int, width: int, height: int):
        """设置视口矩形区域"""
        try:
            self.engine_obj.set_viewport_rect(x, y, width, height)
        except Exception as e:
            raise RuntimeError(f"Viewport.set_viewport_rect 失败: {e}") from e

    def pick_actor_at_pixel(self, x: int, y: int):
        """在像素坐标处拾取 Actor"""
        try:
            self.engine_obj.pick_actor_at_pixel(x, y)
        except Exception as e:
            raise RuntimeError(f"Viewport.pick_actor_at_pixel 失败: {e}") from e

    def save_screenshot(self, path: str):
        """保存截图到文件"""
        try:
            self.engine_obj.save_screenshot(path)
        except Exception as e:
            raise RuntimeError(f"Viewport.save_screenshot 失败: {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            'name': self.name,
            'width': self.width,
            'height': self.height,
            'engine_obj': self.engine_obj,
        }

    def __repr__(self):
        return f"Viewport(name={self.name}, width={self.width}, height={self.height})"
