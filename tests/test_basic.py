"""v0.1 备忘录 + v0.2 日程 + v0.3 项目 测试。"""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from lingyi.db import get_db
from lingyi.models import Memo, Schedule, Project


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
        clinic_days = ["Tuesday", "Wednesday", "Thursday"]
        if today_name in clinic_days:
            assert len(clinics) > 0
        else:
            assert len(clinics) == 0

    def test_init_practice(self, tmp_db):
        from lingyi.schedule import init_practice
        items = init_practice()
        assert len(items) == 7
        assert items[0].type == "practice"
        assert all("练功" in s.description for s in items)

    def test_init_practice_idempotent(self, tmp_db):
        from lingyi.schedule import init_practice
        init_practice()
        items2 = init_practice()
        assert len(items2) == 7

    def test_practice_remind(self, tmp_db):
        from lingyi.schedule import init_practice, check_practice_remind
        init_practice()
        practice = check_practice_remind()
        assert len(practice) == 1
        assert "练功" in practice[0].description

    def test_schedule_cli_practice(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_prac.db")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["schedule", "init", "practice"])
        assert r.exit_code == 0
        assert "7" in r.output
        r = runner.invoke(cli, ["schedule", "list", "--type", "practice"])
        assert "练功" in r.output


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


# ── v0.3 项目 ──────────────────────────────────────────

class TestProject:
    def test_init_projects(self, tmp_db):
        from lingyi.project import init_projects
        items = init_projects()
        assert len(items) == 14
        names = [p.name for p in items]
        assert "LingFlow" in names
        assert "灵知系统" in names

    def test_init_projects_idempotent(self, tmp_db):
        from lingyi.project import init_projects
        items1 = init_projects()
        items2 = init_projects()
        assert len(items1) == len(items2) == 14

    def test_add_project(self, tmp_db):
        from lingyi.project import add_project
        p = add_project("TestProj", alias="测试", priority="P1", category="core",
                        description="测试项目", energy_pct=50)
        assert p.id == 1
        assert p.name == "TestProj"
        assert p.alias == "测试"
        assert p.priority == "P1"
        assert p.energy_pct == 50

    def test_list_projects(self, tmp_db):
        from lingyi.project import init_projects, list_projects
        init_projects()
        all_projects = list_projects()
        assert len(all_projects) == 14

    def test_list_projects_by_status(self, tmp_db):
        from lingyi.project import init_projects, list_projects
        init_projects()
        active = list_projects(status="active")
        assert len(active) == 5
        assert all(p.status == "active" for p in active)

    def test_list_projects_by_category(self, tmp_db):
        from lingyi.project import init_projects, list_projects
        init_projects()
        tools = list_projects(category="tool")
        assert len(tools) == 6
        assert all(p.category == "tool" for p in tools)

    def test_show_project_by_name(self, tmp_db):
        from lingyi.project import init_projects, show_project
        init_projects()
        p = show_project("LingFlow")
        assert p is not None
        assert p.alias == "灵通"

    def test_show_project_by_alias(self, tmp_db):
        from lingyi.project import init_projects, show_project
        init_projects()
        p = show_project("灵克")
        assert p is not None
        assert p.name == "LingClaude"

    def test_show_project_not_found(self, tmp_db):
        from lingyi.project import show_project
        assert show_project("不存在") is None

    def test_update_project(self, tmp_db):
        from lingyi.project import init_projects, update_project, show_project
        init_projects()
        p = update_project("灵知", priority="P0", notes="重要")
        assert p is not None
        assert p.priority == "P0"
        assert p.notes == "重要"
        p2 = show_project("灵知系统")
        assert p2.priority == "P0"

    def test_update_project_not_found(self, tmp_db):
        from lingyi.project import update_project
        assert update_project("不存在", status="active") is None

    def test_format_project_short(self, tmp_db):
        from lingyi.project import init_projects, format_project_short, show_project
        init_projects()
        p = show_project("LingFlow")
        text = format_project_short(p)
        assert "LingFlow" in text
        assert "灵通" in text
        assert "活跃" in text

    def test_format_project_detail(self, tmp_db):
        from lingyi.project import init_projects, format_project_detail, show_project
        init_projects()
        p = show_project("LingYi")
        text = format_project_detail(p)
        assert "LingYi" in text
        assert "灵依" in text
        assert "优先级" in text

    def test_format_project_kanban(self, tmp_db):
        from lingyi.project import init_projects, format_project_kanban
        init_projects()
        text = format_project_kanban()
        assert "活跃" in text
        assert "维护" in text
        assert "暂停" in text
        assert "归档" in text
        assert "LingFlow" in text

    def test_project_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_proj.db")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["project", "init"])
        assert r.exit_code == 0
        assert "14" in r.output
        r = runner.invoke(cli, ["project", "list"])
        assert "LingFlow" in r.output
        r = runner.invoke(cli, ["project", "show", "灵通"])
        assert "LingFlow" in r.output
        r = runner.invoke(cli, ["project", "list", "--status", "active"])
        assert "LingFlow" in r.output
        r = runner.invoke(cli, ["project", "show", "不存在"])
        assert "不存在" in r.output
