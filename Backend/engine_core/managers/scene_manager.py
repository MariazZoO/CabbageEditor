"""
Scene Manager - Data-Oriented Programming (DOP) 风格
数据和操作分离，使用纯函数管理 Scene 资源
"""
from __future__ import annotations
from typing import Optional, List, Dict
from ..entities.scene import Scene

# ============================================================================
# 数据存储：模块级字典
# ============================================================================
_scenes: Dict[str, Scene] = {}


# ============================================================================
# 查询操作：纯函数
# ============================================================================
def get(name: str) -> Optional[Scene]:
    """获取指定名称的 Scene"""
    return _scenes.get(name)


def has(name: str) -> bool:
    """检查 Scene 是否存在"""
    return name in _scenes


def list_all() -> List[str]:
    """列出所有 Scene 名称"""
    return list(_scenes.keys())


def count() -> int:
    """获取 Scene 总数"""
    return len(_scenes)


# ============================================================================
# 创建操作：修改数据
# ============================================================================
def create(name: str) -> Scene:
    """创建新的 Scene"""
    if name in _scenes:
        # 如果已存在，直接返回（兼容旧逻辑）
        return _scenes[name]
    scene = Scene(name=name)
    _scenes[name] = scene
    return scene


def register(name: str, scene: Scene) -> None:
    """注册已存在的 Scene"""
    if name in _scenes:
        raise ValueError(f"Scene '{name}' already registered")
    _scenes[name] = scene


def get_or_create(name: str) -> Scene:
    """获取或创建 Scene（推荐）"""
    existing = get(name)
    if existing is not None:
        return existing
    return create(name)


# ============================================================================
# 删除操作：修改数据
# ============================================================================
def remove(name: str) -> bool:
    """删除指定名称的 Scene"""
    if name in _scenes:
        del _scenes[name]
        return True
    return False


def clear() -> None:
    """清空所有 Scene"""
    _scenes.clear()


# ============================================================================
# 批量操作
# ============================================================================
def create_batch(scene_names: List[str]) -> List[Scene]:
    """批量创建 Scene"""
    results = []
    for name in scene_names:
        scene = get_or_create(name)
        results.append(scene)
    return results


def remove_batch(names: List[str]) -> int:
    """批量删除 Scene，返回删除的数量"""
    count = 0
    for name in names:
        if remove(name):
            count += 1
    return count


# ============================================================================
# 调试与监控
# ============================================================================
def get_all() -> Dict[str, Scene]:
    """获取所有 Scene（用于调试）"""
    return _scenes.copy()


def print_state() -> None:
    """打印当前状态（用于调试）"""
    print(f"[SceneManager] Total: {count()}")
    for name in list_all():
        scene = get(name)
        print(f"  - {name}: {scene}")


# ============================================================================
# 向后兼容：类包装器（可选）
# ============================================================================
class SceneManager:
    """向后兼容的类包装器，内部调用 DOP 函数"""

    @staticmethod
    def create_scene(scene_name: str) -> Scene:
        return create(scene_name)

    @staticmethod
    def get_scene(scene_name: str) -> Optional[Scene]:
        return get(scene_name)

    @staticmethod
    def delete_scene(scene_name: str) -> bool:
        return remove(scene_name)

    @staticmethod
    def has_scene(scene_name: str) -> bool:
        return has(scene_name)

    @staticmethod
    def list_scenes() -> List[str]:
        return list_all()

    @staticmethod
    def get_or_create(scene_name: str) -> Scene:
        return get_or_create(scene_name)
