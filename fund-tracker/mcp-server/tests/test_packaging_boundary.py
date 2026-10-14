"""Static architecture guards for the desktop-only MCP adapter and Android source manifest."""
import ast
import json
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parents[2]
FORBIDDEN = {"mcp", "mcp_types", "fastmcp", "fund_tracker_mcp"}


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            yield node.module.split(".")[0]


def test_backend_and_android_application_do_not_import_mcp():
    backend = ROOT / "backend/app"
    android = ROOT / "frontend/src-tauri/plugins/fund-backend/android/src/main/python"
    for path in [*backend.rglob("*.py"), *android.rglob("*.py")]:
        assert FORBIDDEN.isdisjoint(imported_modules(path)), path


def test_android_and_backend_dependencies_do_not_include_desktop_sdk():
    paths = [ROOT / "backend/requirements.txt", ROOT / "frontend/src-tauri/plugins/fund-backend/android/requirements-android.txt"]
    for path in paths:
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            name = re.split(r"[<>=\[; ]", line.strip(), maxsplit=1)[0].replace("-", "_").lower()
            assert name not in FORBIDDEN, (path, line)


def test_android_source_sync_is_limited_to_backend_app_not_the_repo_root():
    android = ROOT / "frontend/src-tauri/plugins/fund-backend/android"
    gradle = (android / "build.gradle.kts").read_text(encoding="utf-8")
    match = re.search(r'from\(file\("([^"\n]+)"\)\)\s*\{\s*include\("app/\*\*"\)', gradle)
    assert match, "Android Python source sync must explicitly include only backend app/**"
    source_root = (android / match.group(1)).resolve()
    assert source_root == (ROOT / "backend").resolve()
    assert not (ROOT / "mcp-server").is_relative_to(source_root)


def test_mcp_distribution_and_imports_are_independent_of_backend():
    project = ROOT / "mcp-server"
    config = tomllib.loads((project / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["tool"]["setuptools"]["packages"]["find"]["include"] == ["fund_tracker_mcp*"]
    for path in (project / "fund_tracker_mcp").glob("*.py"):
        assert {"app", "sqlalchemy", "pandas", "akshare", "fastapi"}.isdisjoint(imported_modules(path)), path


def test_tauri_resources_cannot_include_the_mcp_tree_or_an_ancestor_directory():
    tauri = ROOT / "frontend/src-tauri"
    bundle = json.loads((tauri / "tauri.conf.json").read_text(encoding="utf-8-sig"))["bundle"]
    resources = bundle.get("resources", [])
    sources = resources.keys() if isinstance(resources, dict) else resources
    mcp_root = (ROOT / "mcp-server").resolve()
    for source in sources:
        prefix = re.split(r"[*?]", source, maxsplit=1)[0]
        candidate = (tauri / prefix).resolve()
        assert not candidate.is_relative_to(mcp_root), source
        assert not mcp_root.is_relative_to(candidate), source
    assert all("mcp" not in path.lower() for path in bundle.get("externalBin", []))
