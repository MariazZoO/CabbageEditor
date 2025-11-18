"""
CoronaEngine Core - Python 绑定与辅助工具

目录结构：
- components/   : 组件（Geometry, Optics, Mechanics, Kinematics, Acoustics）
- entities/     : 核心实体（Actor, Camera, Viewport, Scene, Environment）
- managers/     : DOP 风格的资源管理器（所有 *Manager）
- engine_import.py            : 引擎加载
- engine_object_factory.py    : 对象工厂
- corona_engine_fallback.py   : Fallback 实现
"""

# ============================================================================
# Components - 组件
# ============================================================================
from .components import (
    Geometry,
    Optics,
    Mechanics,
    Kinematics,
    Acoustics,
)

# ============================================================================
# Entities - 核心实体
# ============================================================================
from .entities import (
    Actor,
    Camera,
    Viewport,
    Scene,
    Environment,
)

# ============================================================================
# Managers - 资源管理器（DOP 风格）
# ============================================================================
from .managers import (
    # 类包装器（OOP 兼容）
    SceneManager,
    ActorManager,
    CameraManager,
    ViewportManager,
    EnvironmentManager,
    GeometryManager,
    OpticsManager,
    MechanicsManager,
    KinematicsManager,
    AcousticsManager,
    # 模块（DOP 风格，用于高级用法）
    scene_manager,
    actor_manager,
    camera_manager,
    viewport_manager,
    environment_manager,
    geometry_manager,
    optics_manager,
    mechanics_manager,
    kinematics_manager,
    acoustics_manager,
)

# ============================================================================
# Utilities - 工具
# ============================================================================
from .engine_object_factory import EngineObjectFactory
from .engine_import import load_corona_engine
from .corona_engine_fallback import CoronaEngine

# ============================================================================
# Exports
# ============================================================================
__all__ = [
    # Components
    "Geometry",
    "Optics",
    "Mechanics",
    "Kinematics",
    "Acoustics",
    # Entities
    "Actor",
    "Camera",
    "Viewport",
    "Scene",
    "Environment",
    # Managers (OOP style)
    "SceneManager",
    "ActorManager",
    "CameraManager",
    "ViewportManager",
    "EnvironmentManager",
    "GeometryManager",
    "OpticsManager",
    "MechanicsManager",
    "KinematicsManager",
    "AcousticsManager",
    # Managers (DOP modules)
    "scene_manager",
    "actor_manager",
    "camera_manager",
    "viewport_manager",
    "environment_manager",
    "geometry_manager",
    "optics_manager",
    "mechanics_manager",
    "kinematics_manager",
    "acoustics_manager",
    # Utilities
    "EngineObjectFactory",
    "load_corona_engine",
    "CoronaEngine",
]
