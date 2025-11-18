"""
Actor Manager - Data-Oriented Programming (DOP) 风格
数据和操作分离，使用纯函数管理 Actor 资源
"""
from __future__ import annotations
from typing import Optional, List, Dict
from ..entities.actor import Actor

# ============================================================================
# 数据存储：模块级字典
# ============================================================================
_actors: Dict[str, Actor] = {}


# ============================================================================
# 查询操作：纯函数
# ============================================================================
def get(name: str) -> Optional[Actor]:
    """获取指定名称的 Actor"""
    return _actors.get(name)


def has(name: str) -> bool:
    """检查 Actor 是否存在"""
    return name in _actors


def list_all() -> List[str]:
    """列出所有 Actor 名称"""
    return list(_actors.keys())


def count() -> int:
    """获取 Actor 总数"""
    return len(_actors)


# ============================================================================
# 创建操作：修改数据
# ============================================================================
def create(name: str, asset_path: str) -> Actor:
    """创建新的 Actor"""
    if name in _actors:
        raise ValueError(f"Actor '{name}' already exists")
    actor = Actor(asset_path)
    actor.name = name  # override default
    _actors[name] = actor
    return actor


def register(name: str, actor: Actor) -> None:
    """注册已存在的 Actor"""
    if name in _actors:
        raise ValueError(f"Actor '{name}' already registered")
    _actors[name] = actor


def get_or_create(name: str, asset_path: str) -> Actor:
    """获取或创建 Actor（推荐）"""
    existing = get(name)
    if existing is not None:
        return existing
    return create(name, asset_path)


# ============================================================================
# 删除操作：修改数据
# ============================================================================
def remove(name: str) -> bool:
    """删除指定名称的 Actor"""
    if name in _actors:
        del _actors[name]
        return True
    return False


def clear() -> None:
    """清空所有 Actor"""
    _actors.clear()


# ============================================================================
# 批量操作
# ============================================================================
def create_batch(actor_configs: Dict[str, str]) -> List[Actor]:
    """批量创建 Actor

    Args:
        actor_configs: {name: asset_path} 字典
    """
    results = []
    for name, path in actor_configs.items():
        actor = get_or_create(name, path)
        results.append(actor)
    return results


def remove_batch(names: List[str]) -> int:
    """批量删除 Actor，返回删除的数量"""
    count = 0
    for name in names:
        if remove(name):
            count += 1
    return count


def filter_by_path(path_pattern: str) -> List[Actor]:
    """根据路径模式筛选 Actor"""
    return [actor for actor in _actors.values() if path_pattern in actor.path]


# ============================================================================
# 调试与监控
# ============================================================================
def get_all() -> Dict[str, Actor]:
    """获取所有 Actor（用于调试）"""
    return _actors.copy()


def print_state() -> None:
    """打印当前状态（用于调试）"""
    print(f"[ActorManager] Total: {count()}")
    for name in list_all():
        actor = get(name)
        print(f"  - {name}: {actor.path}")


# ============================================================================
# 向后兼容：类包装器（可选）
# ============================================================================
class ActorManager:
    """向后兼容的类包装器，内部调用 DOP 函数"""

    @staticmethod
    def create(name: str, asset_path: str) -> Actor:
        return create(name, asset_path)

    @staticmethod
    def register(name: str, actor: Actor) -> None:
        return register(name, actor)

    @staticmethod
    def get(name: str) -> Optional[Actor]:
        return get(name)

    @staticmethod
    def get_or_create(name: str, asset_path: str) -> Actor:
        return get_or_create(name, asset_path)

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
