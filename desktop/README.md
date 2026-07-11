# StayLux Desktop (PySide6)

Desktop shell that runs the existing Django web UI inside a PySide6 WebEngine view and starts a local server.

## Quick start (dev)

```powershell
# from repo root
C:/Users/LENOVO/Desktop/StayLux/.venv/Scripts/python.exe -m pip install -r web/requirements.txt -r desktop/requirements.txt
C:/Users/LENOVO/Desktop/StayLux/.venv/Scripts/python.exe desktop/main.py
```

## Packaging (Windows)

1. Install PyInstaller:

```powershell
C:/Users/LENOVO/Desktop/StayLux/.venv/Scripts/python.exe -m pip install pyinstaller
```

2. Build the app:

```powershell
C:/Users/LENOVO/Desktop/StayLux/.venv/Scripts/python.exe -m PyInstaller --noconfirm --clean desktop/staylux.spec
```

3. The EXE will be under `dist/StayLux/StayLux.exe`.

## Installer (Windows)

1. Install Inno Setup 6.
2. Build the installer from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_desktop_installer.ps1 -Version 1.0.0
```

3. Installer output:

`dist/installer/StayLux-Setup.exe`

## Notes

- The app stores SQLite and media under `%APPDATA%/StayLux` by default.
- Database settings can still be changed in the app UI to connect to PostgreSQL/Neon.
- Offline-first sync foundation is included:
  - Local writes are journaled into sync events.
  - Background sync loop can push pending events to a remote StayLux backend.
  - Local sync endpoints: `/api/sync/status/`, `/api/sync/config/`, `/api/sync/push/`, `/api/sync/queue/`.

## Sync Environment Variables

- `STAYLUX_SYNC_MODE=offline|online|auto` (default `auto`)
- `STAYLUX_SYNC_ENABLED=1|0` (default `1`)
- `STAYLUX_SYNC_REMOTE_URL=https://your-cloud-host`
- `STAYLUX_SYNC_API_TOKEN=<bearer-token>` (optional)
- `STAYLUX_SYNC_SHARED_SECRET=<shared-secret>` (recommended)
- `STAYLUX_SYNC_INTERVAL=30` (seconds)
