"""数据模型。"""

from dataclasses import dataclass


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


@dataclass
class Project:
    id: int | None = None
    name: str = ""
    alias: str = ""
    status: str = "active"
    priority: str = "P3"
    category: str = "tool"
    description: str = ""
    repo: str = ""
    version: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Plan:
    id: int | None = None
    content: str = ""
    area: str = "编程"
    project: str = ""
    status: str = "todo"
    due_date: str = ""
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""


@dataclass
class Session:
    id: int | None = None
    summary: str = ""
    files: str = ""
    decisions: str = ""
    todos: str = ""
    prefs_noted: str = ""
    created_at: str = ""
