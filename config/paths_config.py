"""
路径配置
"""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathsConfig:
    """路径配置"""
    repo_root: Path
    backend_root: Path
    frontend_dist: Path
    script_dir: Path
    autosave_dir: Path
    config_dir: Path


def get_default_paths() -> PathsConfig:
    """获取默认路径配置"""
    # 从当前文件位置计算项目根目录
    repo_root = Path(__file__).resolve().parents[1]
    backend_root = repo_root / "Backend"
    config_dir = repo_root / "config"
    autosave_dir = repo_root / "autosave"

    # 确保目录存在
    autosave_dir.mkdir(parents=True, exist_ok=True)

    return PathsConfig(
        repo_root=repo_root,
        backend_root=backend_root,
        frontend_dist=repo_root / "Frontend" / "dist" / "index.html",
        script_dir=backend_root / "script",
        autosave_dir=autosave_dir,
        config_dir=config_dir,
    )