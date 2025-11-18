"""
Camera Manager - Data-Oriented Programming (DOP) 风格
数据和操作分离，使用纯函数管理 Camera 资源
"""
from __future__ import annotations
from typing import Optional, List, Dict
from ..entities.camera import Camera

# ============================================================================
# 数据存储：模块级字典 + 依赖登记（camera -> [viewport_names]）
# ============================================================================
_cameras: Dict[str, Camera] = {}
_dependents: Dict[str, List[str]] = {}


# 依赖登记接口（供 ViewportManager 调用）
def register_viewport_dependency(camera_name: str, viewport_name: str) -> None:
    deps = _dependents.setdefault(camera_name, [])
    if viewport_name not in deps:
        deps.append(viewport_name)


def unregister_viewport_dependency(camera_name: str, viewport_name: str) -> None:
    deps = _dependents.get(camera_name)
    if not deps:
        return
    try:
        deps.remove(viewport_name)
    except ValueError:
        pass
    if not deps:
        _dependents.pop(camera_name, None)


# ============================================================================
# 查询操作：纯函数
# ============================================================================
def get(name: str) -> Optional[Camera]:
    """获取指定名称的 Camera"""
    return _cameras.get(name)


def has(name: str) -> bool:
    """检查 Camera 是否存在"""
    return name in _cameras


def list_all() -> List[str]:
    """列出所有 Camera 名称"""
    return list(_cameras.keys())


def count() -> int:
    """获取 Camera 总数"""
    return len(_cameras)


# ============================================================================
# 创建操作：修改数据
# ============================================================================
def create(name: str, **kwargs) -> Camera:
    """创建新的 Camera"""
    if name in _cameras:
        raise ValueError(f"Camera '{name}' already exists")
    camera = Camera(name=name, **kwargs)
    _cameras[name] = camera
    return camera


def register(name: str, camera: Camera) -> None:
    """注册已存在的 Camera"""
    if name in _cameras:
        raise ValueError(f"Camera '{name}' already registered")
    _cameras[name] = camera


def get_or_create(name: str, **kwargs) -> Camera:
    """获取或创建 Camera（推荐）"""
    existing = get(name)
    if existing is not None:
        return existing
    return create(name, **kwargs)


# ============================================================================
# 删除操作：修改数据（包含级联解绑）
# ============================================================================
def _detach_from_all_viewports(camera_name: str) -> None:
    # 为避免循环依赖，在函数内导入
    try:
        from . import viewport_manager as _vp
    except Exception:
        _vp = None
    for vp_name in list(_dependents.get(camera_name, []) or []):
        if _vp is not None:
            try:
                _vp.detach_camera(vp_name)
            except Exception:
                pass
        unregister_viewport_dependency(camera_name, vp_name)


def remove(name: str) -> bool:
    """删除指定名称的 Camera"""
    if name not in _cameras:
        return False
    # 先从所有视口解绑
    _detach_from_all_viewports(name)
    del _cameras[name]
    return True


def clear() -> None:
    """清空所有 Camera（含解绑）"""
    for n in list_all():
        remove(n)


# ============================================================================
# 批量操作
# ============================================================================
def create_batch(camera_configs: Dict[str, dict]) -> List[Camera]:
    """批量创建 Camera"""
    results = []
    for name, kwargs in camera_configs.items():
        cam = get_or_create(name, **kwargs)
        results.append(cam)
    return results


def remove_batch(names: List[str]) -> int:
    """批量删除 Camera，返回删除的数量"""
    count = 0
    for name in names:
        if remove(name):
            count += 1
    return count


# ============================================================================
# 调试与监控
# ============================================================================
def get_all() -> Dict[str, Camera]:
    """获取所有 Camera（用于调试）"""
    return _cameras.copy()


def print_state() -> None:
    """打印当前状态（用于调试）"""
    print(f"[CameraManager] Total: {count()}")
    for name in list_all():
        cam = get(name)
        print(f"  - {name}: dependents={_dependents.get(name, [])}")


# ============================================================================
# 向后兼容：类包装器（可选）
# ============================================================================
class CameraManager:
    """向后兼容的类包装器，内部调用 DOP 函数"""

    @staticmethod
    def create(name: str, **kwargs) -> Camera:
        return create(name, **kwargs)

    @staticmethod
    def register(name: str, camera: Camera) -> None:
        return register(name, camera)

    @staticmethod
    def get(name: str) -> Optional[Camera]:
        return get(name)

    @staticmethod
    def get_or_create(name: str, **kwargs) -> Camera:
        return get_or_create(name, **kwargs)

    @staticmethod
    def remove(name: str) -> bool:
        return remove(name)

    @staticmethod
    def list() -> List[str]:
        return list_all()

    @staticmethod
    def has(name: str) -> bool:
        return has(name)

    @staticmethod
    def clear() -> None:
        return clear()
