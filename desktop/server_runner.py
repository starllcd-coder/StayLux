import os
import sys
import threading
import traceback
import hashlib
from pathlib import Path


def _resolve_base_dir() -> Path:
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        return Path(bundled)
    return Path(__file__).resolve().parents[1]


def _setup_paths() -> Path:
    forced_web_dir = os.environ.get("STAYLUX_WEB_DIR", "").strip()
    if forced_web_dir:
        web_dir = Path(forced_web_dir)
    else:
        root_dir = _resolve_base_dir()
        web_dir = root_dir / "web"
    sys.path.insert(0, str(web_dir))
    return web_dir


def _ensure_appdata() -> None:
    appdata = os.environ.get("STAYLUX_APPDATA")
    if not appdata:
        return
    Path(appdata).mkdir(parents=True, exist_ok=True)


def _schema_state_key(web_dir: Path) -> str:
    """Build a lightweight fingerprint for migration-related source files."""
    hasher = hashlib.sha1()
    hasher.update(str(sys.version_info[:3]).encode("utf-8"))
    for migration_file in sorted(web_dir.rglob("migrations/*.py")):
        if migration_file.name == "__init__.py":
            continue
        try:
            stat = migration_file.stat()
        except OSError:
            continue
        rel = migration_file.relative_to(web_dir)
        hasher.update(str(rel).encode("utf-8"))
        hasher.update(str(stat.st_mtime_ns).encode("utf-8"))
        hasher.update(str(stat.st_size).encode("utf-8"))
    return hasher.hexdigest()


def _should_run_migrations(web_dir: Path) -> tuple[bool, str, Path | None]:
    if os.environ.get("STAYLUX_FORCE_MIGRATE", "0") == "1":
        return True, _schema_state_key(web_dir), None
    if os.environ.get("STAYLUX_SKIP_MIGRATE", "0") == "1":
        return False, _schema_state_key(web_dir), None

    appdata = os.environ.get("STAYLUX_APPDATA", "").strip()
    if not appdata:
        return True, _schema_state_key(web_dir), None

    key = _schema_state_key(web_dir)
    marker = Path(appdata) / "schema_state.txt"
    if not marker.exists():
        return True, key, marker
    try:
        previous = marker.read_text(encoding="utf-8").strip()
    except OSError:
        return True, key, marker
    return previous != key, key, marker


def run_server(port: int) -> int:
    try:
        web_dir = _setup_paths()
        if not web_dir.exists():
            print(f"Web directory not found: {web_dir}")
            return 3
        _ensure_appdata()

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "staylux.settings")

        try:
            import django
            from django.core.management import call_command
            from django.core.wsgi import get_wsgi_application
        except Exception as exc:
            print("Django import failed. Ensure desktop launcher uses project .venv Python.")
            print(f"Interpreter: {sys.executable}")
            print(f"Import error: {exc!r}")
            return 4

        django.setup()
        run_migrate, schema_key, marker = _should_run_migrations(web_dir)
        if run_migrate:
            call_command("migrate", interactive=False)
            if marker is not None:
                try:
                    marker.write_text(schema_key, encoding="utf-8")
                except OSError:
                    pass

        sync_stop = None
        sync_thread = None
        if os.environ.get("STAYLUX_SYNC_LOOP_ENABLED", "1") == "1":
            try:
                from sync_engine.services import start_background_sync_loop

                sync_stop = threading.Event()
                interval = int(os.environ.get("STAYLUX_SYNC_INTERVAL", "30"))
                sync_thread = start_background_sync_loop(stop_event=sync_stop, interval_seconds=interval)
                print(f"Sync loop started (interval={interval}s)")
            except Exception:
                traceback.print_exc()

        from django.conf import settings

        static_root = Path(settings.STATIC_ROOT) if settings.STATIC_ROOT else None
        if static_root:
            static_root.mkdir(parents=True, exist_ok=True)
            ready_flag = static_root / ".ready"
            if not ready_flag.exists():
                call_command("collectstatic", interactive=False, verbosity=0)
                ready_flag.write_text("ok", encoding="utf-8")

        application = get_wsgi_application()

        from waitress import serve

        serve(application, host="127.0.0.1", port=port, threads=8)
        if sync_stop is not None:
            sync_stop.set()
        if sync_thread is not None and sync_thread.is_alive():
            sync_thread.join(timeout=1)
        return 0
    except Exception:
        traceback.print_exc()
        return 1


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: server_runner.py <port>")
        return 2
    try:
        port = int(sys.argv[1])
    except Exception:
        print("Invalid port argument.")
        return 2
    return run_server(port)


if __name__ == "__main__":
    raise SystemExit(main())
