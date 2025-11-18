"""
Managers - Data-Oriented Programming (DOP) 风格的资源管理器
所有 Manager 使用模块级数据存储和纯函数操作
"""

# 导入所有 Manager 模块（用于 DOP 风格直接导入）
from . import scene_manager
from . import actor_manager
from . import camera_manager
from . import viewport_manager
from . import environment_manager
from . import geometry_manager
from . import optics_manager
from . import mechanics_manager
from . import kinematics_manager
from . import acoustics_manager

# 导入类包装器（用于 OOP 风格兼容）
from .scene_manager import SceneManager
from .actor_manager import ActorManager
from .camera_manager import CameraManager
from .viewport_manager import ViewportManager
from .environment_manager import EnvironmentManager
from .geometry_manager import GeometryManager
from .optics_manager import OpticsManager
from .mechanics_manager import MechanicsManager
from .kinematics_manager import KinematicsManager
from .acoustics_manager import AcousticsManager

__all__ = [
    # 模块（DOP 风格）
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
    # 类包装器（OOP 风格）
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
]

