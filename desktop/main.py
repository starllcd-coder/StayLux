import os
import socket
import subprocess
import sys
import threading
import time
import uuid
import secrets
import traceback
import importlib.util
import contextlib
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen

from PySide6.QtCore import QTimer, QUrl, QUrlQuery, QStandardPaths
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox
from PySide6.QtGui import QIcon, QDesktopServices


APP_NAME = "StayLux"


def _documents_exports_dir() -> Path:
    docs = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
    if docs:
        base = Path(docs)
    else:
        base = Path.home() / "Documents"
    target = base / APP_NAME / "exports"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _export_category_for_path(path_text: str, query: QUrlQuery | None = None) -> str:
    path = (path_text or "").lower()
    doc_kind = (query.queryItemValue("doc") or "").lower() if query is not None else ""

    if "/bookings/group/" in path:
        return "agreements"

    if "/billing/invoices/" in path:
        return "receipts" if doc_kind == "receipt" else "invoices"

    if (
        "/guests/report/" in path
        or "/billing/payments/report/" in path
        or "/reports/" in path
    ):
        return "reports"

    return "misc"


class StayLuxWebPage(QWebEnginePage):
    """Desktop-safe navigation for print/download actions."""

    def __init__(self, action_handler=None, profile=None, parent=None):
        if profile is not None:
            super().__init__(profile, parent)
        else:
            super().__init__(parent)
        self._action_handler = action_handler

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        try:
            url_str = (url.toString() or "").lower()
            host = (url.host() or "").lower()
            is_local = host in {"127.0.0.1", "localhost"}
            is_document_route = (
                ("/billing/invoices/" in url_str)
                or ("/bookings/group/" in url_str)
                or ("/guests/report/print/" in url_str)
                or ("/billing/payments/report/print/" in url_str)
                or ("/reports/bookings/print/" in url_str)
                or ("/reports/revenue/print/" in url_str)
                or ("/reports/occupancy/print/" in url_str)
                or ("/reports/maintenance/print/" in url_str)
            )
            is_desktop_doc_action = ("desktop_print=1" in url_str) or ("desktop_save=1" in url_str)
            if is_local and is_document_route and is_desktop_doc_action:
                if callable(self._action_handler):
                    self._action_handler(url)
                    return False
        except Exception:
            traceback.print_exc()
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / APP_NAME


def _load_or_create_secret(appdata_dir: Path, filename: str) -> str:
    """
    Persist a per-install secret in APPDATA so local desktop sessions/tokens
    remain stable without shipping a hardcoded secret inside the bundle.
    """
    secret_file = appdata_dir / filename
    if secret_file.exists():
        try:
            existing = secret_file.read_text(encoding="utf-8").strip()
            if len(existing) >= 32:
                return existing
        except Exception:
            pass

    generated = secrets.token_urlsafe(48)
    try:
        secret_file.write_text(generated, encoding="utf-8")
    except Exception:
        pass
    return generated


def _resolve_server_python(root_dir: Path) -> str:
    # Prefer project virtualenv in development runs.
    if not getattr(sys, "frozen", False):
        venv_py = root_dir / ".venv" / "Scripts" / "python.exe"
        if venv_py.exists():
            return str(venv_py)

    # In packaged/frozen mode (or if venv missing), fall back to current interpreter.
    return sys.executable


def _resolve_bundle_root() -> Path:
    """Resolve the base directory for bundled resources (web/, server_runner.py)."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        if (base / "web").exists():
            return base
        if (base / "_internal" / "web").exists():
            return base / "_internal"
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "web").exists():
            return exe_dir
        if (exe_dir / "_internal" / "web").exists():
            return exe_dir / "_internal"
        return base
    return Path(__file__).resolve().parents[1]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1100, 720)

        # Prepare user document folders for generated files.
        exports_root = _documents_exports_dir()
        for folder in ("agreements", "receipts", "invoices", "reports", "misc"):
            (exports_root / folder).mkdir(parents=True, exist_ok=True)

        # Keep cookies/storage persistent so "Remember Me" survives desktop restarts.
        appdata = _app_data_dir()
        appdata.mkdir(parents=True, exist_ok=True)
        qtweb_dir = appdata / "qtweb"
        (qtweb_dir / "storage").mkdir(parents=True, exist_ok=True)
        (qtweb_dir / "cache").mkdir(parents=True, exist_ok=True)

        # Make profile a child of the web view so teardown order is page -> profile.
        # This avoids Qt warning: "Release of profile requested but WebEnginePage still not deleted."
        self.view = QWebEngineView()
        self._qt_profile = QWebEngineProfile("StayLuxDesktopProfile", self.view)
        self._qt_profile.setPersistentStoragePath(str(qtweb_dir / "storage"))
        self._qt_profile.setCachePath(str(qtweb_dir / "cache"))
        try:
            self._qt_profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        except Exception:
            pass
        try:
            self._qt_profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
        except Exception:
            pass

        self.view.setPage(StayLuxWebPage(self.handle_document_action, profile=self._qt_profile, parent=self.view))
        self.setCentralWidget(self.view)
        self._show_loading_screen()
        self._pending_pdf_action = None
        self._downloads = []
        self.view.page().pdfPrintingFinished.connect(self._on_pdf_printed)
        self.view.page().profile().downloadRequested.connect(self._on_download_requested)

        self._server_proc = None
        self._server_thread = None
        self._server_log = None
        self._server_log_path = None
        self._port = _find_free_port()
        self._start_time = time.time()
        self._startup_timeout = int(os.environ.get("STAYLUX_STARTUP_TIMEOUT", "90"))
        self._root_dir = _resolve_bundle_root()
        self._web_dir = self._root_dir / "web"
        server_script = self._root_dir / "server_runner.py"
        if server_script.exists():
            self._server_script = server_script
        else:
            self._server_script = Path(__file__).resolve().parent / "server_runner.py"
        self._start_server()

        self._ready_timer = QTimer(self)
        self._ready_timer.setInterval(400)
        self._ready_timer.timeout.connect(self._poll_ready)
        self._ready_timer.start()

    def _show_loading_screen(self) -> None:
        self.view.setHtml(
            "<html><body style='margin:0; font-family:Segoe UI, Arial; background:#f7f8fa;'>"
            "<div style='height:100vh; display:flex; align-items:center; justify-content:center;'>"
            "<div style='text-align:center;'>"
            "<div style='font-size:34px; font-weight:800; color:#0b2340; letter-spacing:0.3px;'>StayLux</div>"
            "<div style='margin-top:10px; color:#5b6b83;'>Starting local server...</div>"
            "<div style='margin:16px auto 0; width:220px; height:8px; border-radius:999px; background:#e5eaf2; overflow:hidden;'>"
            "<div style='height:100%; width:45%; background:#0b2340; animation:slxload 1.2s infinite ease-in-out;'></div>"
            "</div>"
            "</div>"
            "</div>"
            "<style>@keyframes slxload{0%{margin-left:-45%}100%{margin-left:100%}}</style>"
            "</body></html>"
        )

    def _start_server(self) -> None:
        appdata = _app_data_dir()
        appdata.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["STAYLUX_APPDATA"] = str(appdata)
        env.setdefault("DJANGO_SETTINGS_MODULE", "staylux.settings")
        env.setdefault("DJANGO_DEBUG", "0")
        env["STAYLUX_PORT"] = str(self._port)
        env["STAYLUX_LOG"] = str(appdata / "desktop_server.log")
        env["STAYLUX_WEB_DIR"] = str(self._web_dir)
        env.setdefault("STAYLUX_NODE_ID", f"desktop-{uuid.uuid4().hex[:8]}")
        env.setdefault("STAYLUX_SYNC_LOOP_ENABLED", "1")
        env.setdefault("STAYLUX_SYNC_INTERVAL", "30")
        env.setdefault("STAYLUX_SYNC_MODE", "auto")
        env.setdefault("DJANGO_SECRET_KEY", _load_or_create_secret(appdata, "django_secret.key"))
        env.setdefault("STAYLUX_SYNC_SHARED_SECRET", _load_or_create_secret(appdata, "sync_shared_secret.key"))

        log_path = appdata / "desktop_server.log"
        self._server_log_path = log_path
        self._server_log = open(log_path, "a", encoding="utf-8")
        mode = os.environ.get("STAYLUX_DESKTOP_SERVER_MODE", "inprocess").lower()
        if mode == "subprocess":
            python_exec = _resolve_server_python(self._root_dir)
            self._launch_server_subprocess(python_exec, env)
            return

        self._server_thread = threading.Thread(
            target=self._run_server_inprocess,
            args=(self._server_script, self._web_dir, env),
            daemon=True,
        )
        self._server_thread.start()

    def _launch_server_subprocess(self, python_exec: str, env: dict) -> None:
        cmd = [python_exec, str(self._server_script), str(self._port)]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._server_proc = subprocess.Popen(
            cmd,
            cwd=str(self._web_dir),
            env=env,
            stdout=self._server_log,
            stderr=self._server_log,
            creationflags=creationflags,
        )

    def _run_server_inprocess(self, server_script: Path, web_dir: Path, env: dict) -> None:
        old_cwd = Path.cwd()
        old_env = {}
        for key, value in env.items():
            old_env[key] = os.environ.get(key)
            os.environ[key] = value
        try:
            os.chdir(web_dir)
            spec = importlib.util.spec_from_file_location("staylux_server_runner_runtime", str(server_script))
            if spec is None or spec.loader is None:
                raise RuntimeError(f"Could not load server runner module from: {server_script}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            run_server = getattr(module, "run_server", None)
            if not callable(run_server):
                raise RuntimeError("server_runner.run_server was not found.")
            with contextlib.redirect_stdout(self._server_log), contextlib.redirect_stderr(self._server_log):
                rc = run_server(int(self._port))
                print(f"Server runner exited with code: {rc}")
                # If current interpreter cannot import Django, retry with project .venv interpreter.
                if rc == 4:
                    fallback_python = _resolve_server_python(self._root_dir)
                    if fallback_python and str(fallback_python).lower() != str(sys.executable).lower():
                        print(f"Retrying desktop backend via subprocess: {fallback_python}")
                        self._launch_server_subprocess(str(fallback_python), env)
        except Exception:
            with contextlib.redirect_stdout(self._server_log), contextlib.redirect_stderr(self._server_log):
                traceback.print_exc()
        finally:
            os.chdir(old_cwd)
            for key, old_value in old_env.items():
                if old_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = old_value

    def _poll_ready(self) -> None:
        url = f"http://127.0.0.1:{self._port}/"
        try:
            with urlopen(url, timeout=0.8):
                self._ready_timer.stop()
                self.view.setUrl(QUrl(url))
        except Exception:
            elapsed = time.time() - self._start_time
            thread_alive = self._server_thread is not None and self._server_thread.is_alive()
            proc_alive = self._server_proc is not None and self._server_proc.poll() is None
            if (thread_alive or proc_alive) and elapsed <= self._startup_timeout:
                return
            if elapsed > self._startup_timeout:
                self._ready_timer.stop()
                log_path = str(self._server_log_path or "")
                self.view.setHtml(
                    "<html><body style='font-family:Segoe UI, Arial; padding:24px;'>"
                    "<h2>StayLux server did not start</h2>"
                    "<p>Please check the server log for details:</p>"
                    f"<p><code>{log_path}</code></p>"
                    "</body></html>"
                )

    def closeEvent(self, event):
        try:
            self._ready_timer.stop()
        except Exception:
            pass
        try:
            page = self.view.page() if self.view else None
            if page is not None:
                try:
                    page.pdfPrintingFinished.disconnect(self._on_pdf_printed)
                except Exception:
                    pass
                try:
                    page.profile().downloadRequested.disconnect(self._on_download_requested)
                except Exception:
                    pass
                page.deleteLater()
        except Exception:
            pass
        if self._server_proc:
            self._server_proc.terminate()
            try:
                self._server_proc.wait(timeout=3)
            except Exception:
                self._server_proc.kill()
        if self._server_log:
            try:
                self._server_log.close()
            except Exception:
                pass
        super().closeEvent(event)

    def handle_document_action(self, url: QUrl) -> None:
        query = QUrlQuery(url)
        is_download = query.queryItemValue("desktop_save") == "1"
        is_print = query.queryItemValue("desktop_print") == "1"
        if not (is_download or is_print):
            self.view.setUrl(url)
            return

        path_text = self.view.url().path() or url.path() or ""
        category = _export_category_for_path(path_text, query=query)
        if "/billing/invoices/" in path_text:
            if category == "receipts":
                default_name = f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            else:
                default_name = f"invoice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        elif "/bookings/group/" in path_text:
            default_name = f"agreement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        elif "/guests/report/print/" in path_text:
            default_name = f"guests_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        elif "/billing/payments/report/print/" in path_text:
            default_name = f"payments_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        elif "/reports/revenue/print/" in path_text:
            default_name = f"revenue_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        elif "/reports/occupancy/print/" in path_text:
            default_name = f"occupancy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        elif "/reports/maintenance/print/" in path_text:
            default_name = f"maintenance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        elif "/reports/bookings/print/" in path_text:
            default_name = f"bookings_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        else:
            default_name = f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        exports_dir = _documents_exports_dir() / category
        exports_dir.mkdir(parents=True, exist_ok=True)

        if is_download:
            suggested = str(exports_dir / default_name)
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save PDF",
                suggested,
                "PDF Files (*.pdf)",
            )
            if not file_path:
                return
            target = file_path
            action = "save"
        else:
            target = str(exports_dir / default_name)
            action = "print"
        self._pending_pdf_action = {"action": action, "path": target}
        self.view.page().printToPdf(target)

    def _on_pdf_printed(self, file_path: str, success: bool) -> None:
        pending = self._pending_pdf_action or {}
        self._pending_pdf_action = None
        if not pending:
            return
        if not success:
            QMessageBox.warning(self, APP_NAME, "Could not generate PDF. Please try again.")
            return
        if pending.get("action") == "print":
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        else:
            QMessageBox.information(self, APP_NAME, f"PDF saved:\n{file_path}")

    def _on_download_requested(self, download) -> None:
        """Handle browser-style file downloads (e.g., guests PDF/Excel exports)."""
        def _read_attr(obj, name: str, default=None):
            value = getattr(obj, name, default)
            if callable(value):
                try:
                    return value()
                except Exception:
                    return default
            return value

        try:
            exports_dir = _documents_exports_dir()
            exports_dir.mkdir(parents=True, exist_ok=True)

            suggested_name = _read_attr(download, "downloadFileName", "") or f"download_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            mime = str(_read_attr(download, "mimeType", "") or "").lower()
            lower_name = suggested_name.lower()
            download_url_obj = _read_attr(download, "url", None)
            download_url = ""
            try:
                download_url = download_url_obj.toString() if download_url_obj is not None else ""
            except Exception:
                download_url = str(download_url_obj or "")
            category = _export_category_for_path(download_url)
            if category == "misc":
                category = "reports" if ("report" in lower_name or lower_name.endswith(".xlsx") or lower_name.endswith(".pdf")) else "misc"
            target_dir = exports_dir / category
            target_dir.mkdir(parents=True, exist_ok=True)
            if lower_name.endswith(".pdf") or "pdf" in mime:
                filter_text = "PDF Files (*.pdf);;All Files (*.*)"
            elif lower_name.endswith(".xlsx") or "spreadsheet" in mime or "excel" in mime:
                filter_text = "Excel Files (*.xlsx);;All Files (*.*)"
            else:
                filter_text = "All Files (*.*)"

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save File",
                str(target_dir / suggested_name),
                filter_text,
            )
            if not file_path:
                download.cancel()
                return

            target = Path(file_path)
            download.setDownloadDirectory(str(target.parent))
            download.setDownloadFileName(target.name)
            self._downloads.append(download)
            download.finished.connect(lambda d=download: self._on_download_finished(d))
            download.accept()
        except Exception:
            traceback.print_exc()

    def _on_download_finished(self, download) -> None:
        def _read_attr(obj, name: str, default=None):
            value = getattr(obj, name, default)
            if callable(value):
                try:
                    return value()
                except Exception:
                    return default
            return value

        try:
            target = Path(str(_read_attr(download, "downloadDirectory", "") or "")) / str(_read_attr(download, "downloadFileName", "") or "")
            completed = True
            try:
                state_val = _read_attr(download, "state", None)
                completed_enum = getattr(download, "DownloadCompleted", None)
                if completed_enum is not None and state_val is not None:
                    completed = int(state_val) == int(completed_enum)
            except Exception:
                pass
            if completed:
                QMessageBox.information(self, APP_NAME, f"File saved:\n{target}")
        finally:
            if download in self._downloads:
                self._downloads.remove(download)


def main() -> None:
    app = QApplication(sys.argv)
    # Resolve icon from bundled runtime paths first, then local project paths.
    icon_path = None
    candidates = []
    bundled = getattr(sys, "_MEIPASS", None)
    if bundled:
        b = Path(bundled)
        candidates.extend(
            [
                b / "assets" / "brand" / "StayLux_multi.ico",
                b / "desktop" / "icon.svg",
            ]
        )
    exe_dir = Path(sys.executable).resolve().parent
    candidates.extend(
        [
            exe_dir / "assets" / "brand" / "StayLux_multi.ico",
            exe_dir / "_internal" / "assets" / "brand" / "StayLux_multi.ico",
            exe_dir / "desktop" / "icon.svg",
            exe_dir / "_internal" / "desktop" / "icon.svg",
            Path(__file__).resolve().parents[1] / "assets" / "brand" / "StayLux_multi.ico",
            Path(__file__).resolve().parents[1] / "desktop" / "icon.svg",
        ]
    )
    for candidate in candidates:
        if candidate.exists():
            icon_path = candidate
            break

    if icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))
    window = MainWindow()
    # Also ensure window has the icon set
    if icon_path:
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
