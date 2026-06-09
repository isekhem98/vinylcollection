"""Vinyl Collection Dashboard — launcher."""
from __future__ import annotations

import json
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return _here


_SETTINGS_FILE = _app_root() / "settings.json"


def _load_settings() -> dict:
    if _SETTINGS_FILE.exists():
        return json.loads(_SETTINGS_FILE.read_text())
    return {}


def _save_settings(settings: dict):
    _SETTINGS_FILE.write_text(json.dumps(settings, indent=2))


def _get_db_path() -> str:
    for i, arg in enumerate(sys.argv):
        if arg == "--db" and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]
            sys.argv.pop(i)
            sys.argv.pop(i)
            settings = _load_settings()
            settings["db_path"] = db_path
            _save_settings(settings)
            return db_path
    settings = _load_settings()
    return settings.get("db_path", str(_app_root() / "vinyl.db"))


def main():
    db_path = _get_db_path()
    import webapp
    webapp.main(db_path=db_path)


if __name__ == "__main__":
    main()
