# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

try:
    spec_path = Path(__file__).resolve()
    root_dir = spec_path.parents[1]
except NameError:
    # __file__ may be undefined when PyInstaller executes the spec via exec().
    # Assume the spec is run from the repo root.
    root_dir = Path.cwd()
    if not (root_dir / "web").exists():
        # Fallback: if invoked from desktop/, move one level up.
        root_dir = root_dir.parent
web_dir = root_dir / "web"


def _collect_web_runtime_data(web_root):
    """
    Include runtime-required Django project files while excluding local/dev
    artifacts and sensitive files that should not ship inside desktop builds.
    """
    skip_dir_names = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".git",
        ".idea",
        ".vscode",
        "tests",
        "test",
    }
    skip_file_names = {
        "db.sqlite3",
        ".env",
        ".env.local",
        ".env.development",
        ".env.production",
        "runserver_mobile.err.log",
        "runserver_mobile.out.log",
        "form_labels_debug.json",
        "gettext_check.json",
        "po_dups.json",
        "check_settings.py",
        "check_settings_verbose.py",
    }
    skip_suffixes = {".pyc", ".pyo", ".log"}

    datas = []
    for f in web_root.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(web_root)
        if any(part in skip_dir_names for part in rel.parts[:-1]):
            continue
        if f.name in skip_file_names:
            continue
        if f.suffix.lower() in skip_suffixes:
            continue
        if f.name.startswith("check_settings"):
            continue
        datas.append((str(f), (Path("web") / rel.parent).as_posix()))
    return datas

django_hidden = collect_submodules("django")
drf_hidden = collect_submodules("rest_framework")
jwt_hidden = collect_submodules("rest_framework_simplejwt")
filters_hidden = collect_submodules("django_filters")
whitenoise_hidden = collect_submodules("whitenoise")
waitress_hidden = collect_submodules("waitress")
openpyxl_hidden = collect_submodules("openpyxl")
reportlab_hidden = collect_submodules("reportlab")

analysis = Analysis(
    [str(root_dir / "desktop" / "main.py")],
    pathex=[str(root_dir)],
    binaries=[],
    datas=[
        *_collect_web_runtime_data(web_dir),
        (str(root_dir / "desktop" / "server_runner.py"), "."),
        (str(root_dir / "assets" / "brand"), "assets/brand"),
        (str(root_dir / "desktop" / "icon.svg"), "desktop"),
    ]
    + collect_data_files("django")
    + collect_data_files("rest_framework")
    + collect_data_files("openpyxl")
    + collect_data_files("reportlab"),
    hiddenimports=[
        "PySide6.QtWebEngineWidgets",
        "sync_engine",
    ]
    + django_hidden
    + drf_hidden
    + jwt_hidden
    + filters_hidden
    + whitenoise_hidden
    + waitress_hidden
    + openpyxl_hidden
    + reportlab_hidden
    + ["waitress"],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="StayLux",
    debug=False,
    icon=str(root_dir / "assets" / "brand" / "StayLux_multi.ico"),
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    name="StayLux",
)
