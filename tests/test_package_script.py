"""scripts/package_plugin.py 的离线测试。

验证打包脚本只收录 AstrBot 会读取的文件（外加必须随源码分发的 LICENSE），
并剔除测试 / 前端源码 / 构建缓存。脚本不是包，用 importlib 按文件路径加载。
"""

from __future__ import annotations

import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "package_plugin.py"


def _load_package_script():
    """按文件路径加载打包脚本模块"""
    spec = importlib.util.spec_from_file_location("package_plugin", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


package_plugin = _load_package_script()


def _repo_version() -> str:
    return package_plugin._read_scalar(REPO_ROOT / "metadata.yaml", "version")


def test_build_package_only_includes_astrbot_files(tmp_path: Path) -> None:
    """从真实仓库打包：只包含 AstrBot 读取的文件，且单一顶层目录"""
    zip_path = package_plugin.build_package(tmp_path)
    assert zip_path.is_file()
    assert zip_path.parent == tmp_path

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()

    top_levels = {name.split("/", 1)[0] for name in names}
    assert top_levels == {f"astrbot_plugin_qq_custom_menu-{_repo_version()}"}

    prefix = top_levels.pop() + "/"
    assert f"{prefix}metadata.yaml" in names
    assert f"{prefix}main.py" in names
    assert f"{prefix}_conf_schema.json" in names
    assert f"{prefix}requirements.txt" in names
    assert f"{prefix}core/web_api.py" in names
    assert f"{prefix}core/sync_runner.py" in names
    assert f"{prefix}.astrbot-plugin/i18n/zh-CN.json" in names
    assert f"{prefix}.astrbot-plugin/i18n/en-US.json" in names
    assert f"{prefix}core/i18n/zh-CN.json" in names
    assert f"{prefix}core/i18n/en-US.json" in names
    assert f"{prefix}pages/dashboard/index.html" in names
    # 分发源码必须随附 AGPL-3.0 文本
    assert f"{prefix}LICENSE" in names

    relative = {name[len(prefix) :] for name in names}
    for excluded in (
        "pyproject.toml",
        "CHANGELOG.md",
        "requirements-dev.txt",
        "AGENTS.md",
    ):
        assert excluded not in relative
    assert not any(name.startswith(("tests/", "web/", ".github/", "scripts/")) for name in relative)
    assert not any(part == "__pycache__" for name in relative for part in name.split("/"))
    assert not any(name.endswith((".pyc", ".pyo")) for name in relative)


def test_build_package_from_custom_root(tmp_path: Path) -> None:
    """最小插件目录：缺失的可选文件被跳过，缓存产物被剔除"""
    root = tmp_path / "plugin"
    (root / "core" / "__pycache__").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "metadata.yaml").write_text("name: demo_plugin\nversion: v1.2.3\n", encoding="utf-8")
    (root / "main.py").write_text("", encoding="utf-8")
    (root / "core" / "app.py").write_text("", encoding="utf-8")
    (root / "core" / "__pycache__" / "app.pyc").write_bytes(b"")
    (root / "tests" / "test_app.py").write_text("", encoding="utf-8")

    zip_path = package_plugin.build_package(tmp_path / "out", root=root)
    assert zip_path == tmp_path / "out" / "demo_plugin-v1.2.3.zip"

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())

    assert names == {
        "demo_plugin-v1.2.3/metadata.yaml",
        "demo_plugin-v1.2.3/main.py",
        "demo_plugin-v1.2.3/core/app.py",
    }


def test_build_package_version_override_and_file_output(tmp_path: Path) -> None:
    """版本号可覆盖，输出参数以 .zip 结尾时直接作为 zip 路径"""
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "metadata.yaml").write_text("name: demo_plugin\nversion: v1.2.3\n", encoding="utf-8")
    (root / "main.py").write_text("", encoding="utf-8")

    zip_path = package_plugin.build_package(tmp_path / "custom.zip", version="v9.9.9", root=root)
    assert zip_path == tmp_path / "custom.zip"

    with zipfile.ZipFile(zip_path) as archive:
        assert set(archive.namelist()) == {
            "demo_plugin-v9.9.9/metadata.yaml",
            "demo_plugin-v9.9.9/main.py",
        }


def test_build_package_requires_metadata(tmp_path: Path) -> None:
    """缺少 metadata.yaml 时直接报错"""
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(SystemExit):
        package_plugin.build_package(tmp_path / "out", root=empty)


def test_build_package_requires_main(tmp_path: Path) -> None:
    """缺少 main.py 时直接报错"""
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "metadata.yaml").write_text("name: demo\nversion: v1.0.0\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        package_plugin.build_package(tmp_path / "out", root=root)


def test_build_package_requires_name_and_version(tmp_path: Path) -> None:
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "main.py").write_text("", encoding="utf-8")
    (root / "metadata.yaml").write_text("display_name: demo\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        package_plugin.build_package(tmp_path / "out", root=root)

    (root / "metadata.yaml").write_text("name: demo\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        package_plugin.build_package(tmp_path / "out", root=root)


def test_build_package_requires_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """收集不到任何文件时报错，而不是写出一个空 zip"""
    root = tmp_path / "plugin"
    root.mkdir()
    (root / "metadata.yaml").write_text("name: demo\nversion: v1.0.0\n", encoding="utf-8")
    (root / "main.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(package_plugin, "_iter_plugin_entries", lambda root: [])

    with pytest.raises(SystemExit):
        package_plugin.build_package(tmp_path / "out", root=root)


def test_read_scalar_handles_quotes_and_comments(tmp_path: Path) -> None:
    metadata = tmp_path / "metadata.yaml"
    metadata.write_text(
        "name: \"demo\"  # comment\nversion: 'v2.0.0'\n",
        encoding="utf-8",
    )

    assert package_plugin._read_scalar(metadata, "name") == "demo"
    assert package_plugin._read_scalar(metadata, "version") == "v2.0.0"


def test_read_scalar_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        package_plugin._read_scalar(tmp_path / "missing.yaml", "name")


def test_main_prints_zip_path(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert package_plugin.main(["-o", str(tmp_path / "out"), "-v", "v2.0.0"]) == 0

    out = capsys.readouterr().out.strip()
    assert out.endswith("astrbot_plugin_qq_custom_menu-v2.0.0.zip")


def test_package_is_reproducible(tmp_path: Path) -> None:
    """相同源码两次打包的字节完全一致（固定时间戳 + 稳定排序）"""
    first = package_plugin.build_package(tmp_path / "a", version="v1.0.0")
    second = package_plugin.build_package(tmp_path / "b", version="v1.0.0")
    assert first.read_bytes() == second.read_bytes()
