"""\nManager 级联一致性自检脚本\n=================================\n\n目的: 持久验证几何与组件、相机与视口之间的依赖登记与级联删除逻辑是否正确。\n\n运行方式:\n    python manager_cascade_test.py\n或在项目根添加路径后运行:\n    python -c "import sys; sys.path.append('E:/project/CoronaEngine/editor/CabbageEditor'); from Backend.tests.manager_cascade_test import run_all; run_all()"\n\n说明:\n- 使用已有模型资源: assets/model/Ball.obj (确保存在)\n- 直接访问内部模块变量(_dependencies 等)用于测试, 属于白盒测试\n- 所有测试之间相互独立, 每个测试前执行 clear()\n"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import List
import traceback

# 确保可以绝对导入 Backend 包
REPO_ROOT = Path(__file__).resolve().parents[2]  # .../editor/CabbageEditor
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

PROJECT_ROOT = Path(REPO_ROOT).parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# 导入被测模块
import Backend.engine_core.managers.geometry_manager as gm
import Backend.engine_core.managers.optics_manager as om
import Backend.engine_core.managers.mechanics_manager as mm
import Backend.engine_core.managers.kinematics_manager as km
import Backend.engine_core.managers.acoustics_manager as am
import Backend.engine_core.managers.camera_manager as camm
import Backend.engine_core.managers.viewport_manager as vpm

# 使用的模型路径 (存在以避免几何构造报错)
MODEL_PATH = str(Path(REPO_ROOT).parents[1] / 'assets' / 'model' / 'Ball.obj')

print(f"[Setup] REPO_ROOT={REPO_ROOT}", flush=True)
print(f"[Setup] PROJECT_ROOT={PROJECT_ROOT}", flush=True)
print(f"[Setup] MODEL_PATH={MODEL_PATH}", flush=True)
print(f"[Setup] Python sys.path size={len(sys.path)}", flush=True)

try:
    import Backend.engine_core as ec  # 试探总入口
    print("[Setup] Imported Backend.engine_core successfully", flush=True)
except Exception as e:
    print("[ERROR] Import Backend.engine_core failed:\n" + traceback.format_exc(), flush=True)

if not os.path.exists(MODEL_PATH):
    print(f"[WARN] 模型文件不存在: {MODEL_PATH}, 几何创建可能失败")

# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def reset_all():
    vpm.clear()
    camm.clear()
    om.clear()
    mm.clear()
    km.clear()
    am.clear()
    gm.clear()


def assert_true(cond: bool, msg: str):
    if not cond:
        raise AssertionError(msg)


def get_dep_count(geometry):
    # 访问内部依赖登记字典
    # geometry 对象 id 为 key
    return len(gm._dependencies.get(id(geometry), []))  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# 测试 1: 创建几何 + 多组件, 删除几何级联清理
# ---------------------------------------------------------------------------

def test_geometry_cascade():
    reset_all()
    g = gm.get_or_create('G1', MODEL_PATH)
    om.get_or_create('Opt1', g)
    mm.get_or_create('Mech1', g)
    km.get_or_create('Kin1', g)
    am.get_or_create('Aco1', g)

    assert_true(get_dep_count(g) == 4, '依赖登记数量应为 4')
    gm.remove('G1')

    assert_true('Opt1' not in om.list_all(), 'Optics 未级联删除')
    assert_true('Mech1' not in mm.list_all(), 'Mechanics 未级联删除')
    assert_true('Kin1' not in km.list_all(), 'Kinematics 未级联删除')
    assert_true('Aco1' not in am.list_all(), 'Acoustics 未级联删除')
    print('[PASS] test_geometry_cascade')

# ---------------------------------------------------------------------------
# 测试 2: 删除单个组件解除依赖
# ---------------------------------------------------------------------------

def test_component_unlink():
    reset_all()
    g = gm.get_or_create('G2', MODEL_PATH)
    om.get_or_create('Opt2', g)
    mm.get_or_create('Mech2', g)
    assert_true(get_dep_count(g) == 2, '依赖数量应为 2')

    om.remove('Opt2')
    assert_true(get_dep_count(g) == 1, '删除 Optics 后依赖数量应为 1')

    mm.remove('Mech2')
    assert_true(get_dep_count(g) == 0, '删除 Mechanics 后依赖数量应为 0')
    print('[PASS] test_component_unlink')

# ---------------------------------------------------------------------------
# 测试 3: remove_by_object 级联删除
# ---------------------------------------------------------------------------

def test_remove_by_object():
    reset_all()
    g = gm.get_or_create('G3', MODEL_PATH)
    om.get_or_create('Opt3', g)
    assert_true(get_dep_count(g) == 1, '依赖数量应为 1')
    gm.remove_by_object(g)
    assert_true('Opt3' not in om.list_all(), 'Optics 未级联删除 (remove_by_object)')
    print('[PASS] test_remove_by_object')

# ---------------------------------------------------------------------------
# 测试 4: 批量创建/批量删除组件后依赖为空
# ---------------------------------------------------------------------------

def test_batch_operations():
    reset_all()
    g = gm.get_or_create('G4', MODEL_PATH)
    geo_list = [g]
    # 创建批量 optics / mechanics
    om.create_batch({'Opt4': g})
    mm.create_batch({'Mech4': g})
    assert_true(get_dep_count(g) == 2, '批量创建后依赖数量应为 2')

    om.remove_batch(['Opt4'])
    assert_true(get_dep_count(g) == 1, '批量删除 Optics 后依赖数量应为 1')

    mm.remove_batch(['Mech4'])
    assert_true(get_dep_count(g) == 0, '批量删除 Mechanics 后依赖数量应为 0')
    print('[PASS] test_batch_operations')

# ---------------------------------------------------------------------------
# 测试 5: 相机与视口的依赖登记与解绑级联
# ---------------------------------------------------------------------------

def test_camera_viewport_cascade():
    reset_all()
    camm.get_or_create('MainCam')
    vpm.get_or_create('MainVP', 800, 600)
    vpm.attach_camera('MainVP', 'MainCam')

    # 检查相机依赖表
    dep_list = camm._dependents.get('MainCam', [])  # type: ignore[attr-defined]
    assert_true(dep_list == ['MainVP'], '相机依赖视口登记失败')

    # 删除相机: 视口应自动 detach (仍存在但无相机)
    camm.remove('MainCam')
    vp = vpm.get('MainVP')
    assert_true(vp is not None, '视口不应被删除')
    assert_true(vp.get_camera() is None, '相机删除后视口未自动解绑')
    print('[PASS] test_camera_viewport_cascade')

# ---------------------------------------------------------------------------
# 测试 6: 删除视口解除相机依赖
# ---------------------------------------------------------------------------

def test_viewport_remove_unlinks_camera():
    reset_all()
    camm.get_or_create('CamA')
    vpm.get_or_create('VPA', 640, 480)
    vpm.attach_camera('VPA', 'CamA')
    assert_true(camm._dependents.get('CamA') == ['VPA'], '依赖登记失败')  # type: ignore[attr-defined]

    vpm.remove('VPA')
    assert_true(camm._dependents.get('CamA') == [] or 'CamA' not in camm._dependents, '视口删除后未解除相机依赖')  # type: ignore[attr-defined]
    print('[PASS] test_viewport_remove_unlinks_camera')

# ---------------------------------------------------------------------------
# 汇总运行
# ---------------------------------------------------------------------------

def run_all():
    tests = [
        test_geometry_cascade,
        test_component_unlink,
        test_remove_by_object,
        test_batch_operations,
        test_camera_viewport_cascade,
        test_viewport_remove_unlinks_camera,
    ]
    for fn in tests:
        print(f"[RUN] {fn.__name__}", flush=True)
        try:
            fn()
        except Exception:
            print(traceback.format_exc(), flush=True)
            raise
    print('\n[SUMMARY] 所有级联与依赖测试通过')

if __name__ == '__main__':
    run_all()
