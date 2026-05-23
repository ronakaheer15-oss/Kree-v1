from pathlib import Path


def test_runtime_dev_paths_resolve_to_project_root():
    from kree.core import runtime

    project_root = Path(__file__).resolve().parents[3]
    assert runtime.BUNDLE_DIR == project_root
    assert runtime.EXE_DIR == project_root
    assert runtime.CONFIG_DIR == project_root / "config"
    assert runtime.ASSETS_DIR == project_root / "assets"
