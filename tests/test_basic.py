"""v0.1 备忘录 + v0.2 日程 测试。"""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from lingyi.db import get_db
from lingyi.models import Memo, Schedule


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
    monkeypatch.setattr("lingyi.db.DB_PATH", db_path)
    return str(db_path)


# ── v0.1 备忘录 ─────────────────────────────────────

class TestMemo:
    def test_add(self, tmp_db):
        from lingyi.memo import add_memo
        m = add_memo("测试备忘")
        assert m.id == 1
        assert m.content == "测试备忘"
        assert m.created_at

    def test_list(self, tmp_db):
        from lingyi.memo import add_memo, list_memos
        add_memo("第一条")
        add_memo("第二条")
        memos = list_memos()
        assert len(memos) == 2
        assert memos[0].content == "第二条"

    def test_show(self, tmp_db):
        from lingyi.memo import add_memo, show_memo
        m = add_memo("可查的")
        found = show_memo(m.id)
        assert found.content == "可查的"
        assert show_memo(999) is None

    def test_delete(self, tmp_db):
        from lingyi.memo import add_memo, delete_memo
        m = add_memo("要删的")
        assert delete_memo(m.id) is True
        assert delete_memo(999) is False


# ── v0.2 日程 ────────────────────────────────────────

class TestSchedule:
    def test_init_clinic(self, tmp_db):
        from lingyi.schedule import init_clinic
        items = init_clinic()
        assert len(items) == 6
        assert items[0].type == "clinic"

    def test_init_clinic_idempotent(self, tmp_db):
        from lingyi.schedule import init_clinic
        init_clinic()
        items2 = init_clinic()
        assert len(items2) == 6

    def test_add_and_list(self, tmp_db):
        from lingyi.schedule import add_schedule, list_schedules
        add_schedule("study", "Saturday", "morning", "编程")
        items = list_schedules()
        study = [s for s in items if s.type == "study"]
        assert len(study) == 1
        assert study[0].day == "Saturday"

    def test_show(self, tmp_db):
        from lingyi.schedule import add_schedule, show_schedule
        s = add_schedule("study", "Sunday", "evening")
        found = show_schedule(s.id)
        assert found.day == "Sunday"
        assert show_schedule(999) is None

    def test_update(self, tmp_db):
        from lingyi.schedule import add_schedule, update_schedule
        s = add_schedule("study", "Monday", "morning")
        updated = update_schedule(s.id, day="Tuesday", time_slot="afternoon")
        assert updated.day == "Tuesday"
        assert updated.time_slot == "afternoon"

    def test_cancel(self, tmp_db):
        from lingyi.schedule import add_schedule, cancel_schedule, list_schedules
        s = add_schedule("study", "Wednesday", "morning")
        assert cancel_schedule(s.id) is True
        active = list_schedules(active_only=True)
        assert all(s.id != item.id for item in active)

    def test_list_by_type(self, tmp_db):
        from lingyi.schedule import add_schedule, list_schedules
        add_schedule("study", "Saturday", "morning")
        add_schedule("study", "Sunday", "morning")
        study = list_schedules(schedule_type="study")
        assert len(study) == 2

    def test_today_schedules(self, tmp_db):
        from lingyi.schedule import add_schedule, today_schedules
        from datetime import date
        today_name = date.today().strftime("%A")
        add_schedule("test_today", today_name, "morning")
        add_schedule("test_today", "Sunday", "morning")
        items = today_schedules()
        today_items = [s for s in items if s.type == "test_today"]
        assert len(today_items) == 1

    def test_remind(self, tmp_db):
        from lingyi.schedule import init_clinic, check_remind
        from datetime import date
        init_clinic()
        clinics = check_remind()
        today_name = date.today().strftime("%A")
        expected = [
            ("Monday", "afternoon"), ("Tuesday", "morning"),
            ("Wednesday", "afternoon"), ("Thursday", "morning"),
            ("Friday", "afternoon"), ("Saturday", "morning"),
        ]
        has_clinic_today = any(d == today_name for d, _ in expected)
        if has_clinic_today:
            assert len(clinics) > 0
        else:
            assert len(clinics) == 0


# ── CLI 集成测试 ─────────────────────────────────────

class TestCLI:
    def test_memo_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_test.db")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["memo", "add", "CLI测试"])
        assert r.exit_code == 0
        assert "已添加" in r.output
        r = runner.invoke(cli, ["memo", "list"])
        assert "CLI测试" in r.output

    def test_schedule_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_sched.db")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["schedule", "init", "clinic"])
        assert r.exit_code == 0
        assert "6" in r.output
        r = runner.invoke(cli, ["schedule", "list"])
        assert "clinic" in r.output
        r = runner.invoke(cli, ["schedule", "week"])
        assert "本周排班" in r.output
