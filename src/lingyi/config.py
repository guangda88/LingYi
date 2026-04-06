"""加载用户私有预设数据（~/.lingyi/presets.json）。"""

import json

from .db import DB_DIR

PRESETS_PATH = DB_DIR / "presets.json"


def load_presets() -> dict:
    if not PRESETS_PATH.exists():
        return {"schedules": {}, "projects": [], "patrol_paths": {}}
    return json.loads(PRESETS_PATH.read_text(encoding="utf-8"))


def load_schedule_preset(preset_name: str) -> list[tuple[str, str, str]]:
    presets = load_presets()
    items = presets.get("schedules", {}).get(preset_name, [])
    return [(i["day"], i["time_slot"], i.get("description", "")) for i in items]


def load_project_presets() -> list[dict]:
    presets = load_presets()
    return presets.get("projects", [])


def load_patrol_paths() -> dict[str, str]:
    presets = load_presets()
    return presets.get("patrol_paths", {})
