"""灵家议事厅配置 — 常量、端点映射、状态持久化。"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

_KEY_FILE = Path.home() / ".dashscope_api_key"
_COUNCIL_STATE_PATH = Path.home() / ".lingmessage" / "council_state.json"
MAX_TURNS_PER_MEMBER = 2
MAX_MESSAGES_PER_DISCUSSION = 15


MEMBER_ENDPOINTS = {
    "lingzhi": {
        "url": "http://127.0.0.1:8000/api/v1/discuss",
        "source": "real",
    },
    "lingyi": {
        "url": "https://127.0.0.1:8900/api/discuss",
        "source": "real",
    },
    "lingclaude": {
        "url": "http://127.0.0.1:8700/api/lingmessage/notify",
        "source": "real",
        "notify_only": True,
    },
    "lingzhi_auto": {
        "url": "http://127.0.0.1:8011/api/lingmessage/notify",
        "source": "real",
        "notify_only": True,
        "member_id": "lingzhi",
    },
    "lingminopt": {
        "url": "http://127.0.0.1:8002/api/lingmessage/notify",
        "source": "real",
        "notify_only": True,
    },
    "lingresearch": {
        "url": "http://127.0.0.1:8003/api/lingmessage/notify",
        "source": "real",
        "notify_only": True,
    },
    "lingyang": {
        "url": "http://127.0.0.1:8004/api/lingmessage/notify",
        "source": "real",
        "notify_only": True,
    },
    "lingflow": {
        "url": "http://127.0.0.1:8100/api/v1/discuss",
        "source": "real",
        "notify_only": True,
    },
}


@dataclass
class CouncilState:
    last_scan_time: str = ""
    processed_messages: list = field(default_factory=list)
    wake_count: int = 0
    discussions_monitored: int = 0
    started_at: str = ""


def _load_state() -> CouncilState:
    if _COUNCIL_STATE_PATH.exists():
        try:
            data = json.loads(_COUNCIL_STATE_PATH.read_text(encoding="utf-8"))
            return CouncilState(**{k: v for k, v in data.items() if k in CouncilState.__dataclass_fields__})
        except Exception:
            pass
    return CouncilState()


def _save_state(state: CouncilState) -> None:
    _COUNCIL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _COUNCIL_STATE_PATH.write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2), encoding="utf-8"
    )
