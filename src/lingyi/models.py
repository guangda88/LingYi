"""数据模型。"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Memo:
    id: int | None = None
    content: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Schedule:
    id: int | None = None
    type: str = ""
    day: str = ""
    time_slot: str = ""
    description: str = ""
    is_active: bool = True
    created_at: str = ""

    @property
    def day_index(self) -> int:
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return order.index(self.day) if self.day in order else 7
