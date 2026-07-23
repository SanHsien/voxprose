"""
Per-screen window position memory.

Stored in its own file (ui_positions.json) instead of config_local.json:
SettingsWindow holds a config snapshot from its creation time and rewrites
config_local.json wholesale on save, which would clobber any key written
between snapshot and save. A dedicated file sidesteps that entirely.

Data layout:
{
  "indicator": {
    "_last": "\\\\.\\DISPLAY1",
    "\\\\.\\DISPLAY1": [dx, dy],   # offset from screen availableGeometry top-left
    "\\\\.\\DISPLAY2": [dx, dy]
  },
  "floating_button": { ... }
}
"""
import json
import logging
import threading

from paths import APP_DATA_DIR

log = logging.getLogger("voicetype.ui")

POSITIONS_PATH = APP_DATA_DIR / "ui_positions.json"
_lock = threading.Lock()


def _load_all() -> dict:
    try:
        with open(POSITIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        log.debug(f"[positions] Failed to load {POSITIONS_PATH}: {e}")
        return {}


def get_position(window_key: str, screen_name: str):
    """Return saved [dx, dy] offset for the window on that screen, or None."""
    pos = _load_all().get(window_key, {}).get(screen_name)
    if (isinstance(pos, list) and len(pos) == 2
            and all(isinstance(v, (int, float)) for v in pos)):
        return int(pos[0]), int(pos[1])
    return None


def get_last_screen(window_key: str):
    """Return the screen name the window was last dropped on, or None."""
    name = _load_all().get(window_key, {}).get("_last")
    return name if isinstance(name, str) else None


def save_position(window_key: str, screen_name: str, dx: int, dy: int) -> None:
    with _lock:
        data = _load_all()
        entry = data.setdefault(window_key, {})
        entry[screen_name] = [int(dx), int(dy)]
        entry["_last"] = screen_name
        try:
            with open(POSITIONS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log.warning(f"[positions] Failed to save {window_key}: {e}")


def clamp_into(available, x: int, y: int, w: int, h: int):
    """Clamp a window top-left so the window stays inside availableGeometry.
    Guards against saved offsets from a since-changed resolution."""
    max_x = available.x() + available.width() - w
    max_y = available.y() + available.height() - h
    return max(available.x(), min(x, max_x)), max(available.y(), min(y, max_y))
