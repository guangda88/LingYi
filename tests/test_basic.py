"""v0.1 备忘录 + v0.2 日程 + v0.3 项目 + v0.4 计划 + 配置/巡检 测试。"""

import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from lingyi.db import get_db
from lingyi.models import Memo, Schedule, Project, Plan


_TEST_PRESETS = Path(__file__).parent / "test_presets.json"


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
    monkeypatch.setattr("lingyi.db.DB_PATH", db_path)
    monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
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
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
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
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
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
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
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
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
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


# ── v0.4 计划 ──────────────────────────────────────────

class TestPlan:
    def test_add_plan(self, tmp_db):
        from lingyi.plan import add_plan
        p = add_plan("灵知系统安全加固", area="编程", project="灵知", due_date="2026-04-10")
        assert p.id == 1
        assert p.content == "灵知系统安全加固"
        assert p.area == "编程"
        assert p.project == "灵知"
        assert p.due_date == "2026-04-10"
        assert p.status == "todo"
        assert p.created_at

    def test_add_plan_defaults(self, tmp_db):
        from lingyi.plan import add_plan
        p = add_plan("撰写AI+中医论文大纲")
        assert p.area == "编程"
        assert p.project == ""
        assert p.status == "todo"

    def test_list_plans(self, tmp_db):
        from lingyi.plan import add_plan, list_plans
        add_plan("任务A", area="编程")
        add_plan("任务B", area="论文")
        add_plan("任务C", area="编程")
        all_plans = list_plans()
        assert len(all_plans) == 3

    def test_list_plans_by_area(self, tmp_db):
        from lingyi.plan import add_plan, list_plans
        add_plan("任务A", area="编程")
        add_plan("任务B", area="论文")
        add_plan("任务C", area="编程")
        code_plans = list_plans(area="编程")
        assert len(code_plans) == 2
        assert all(p.area == "编程" for p in code_plans)

    def test_list_plans_by_status(self, tmp_db):
        from lingyi.plan import add_plan, list_plans, done_plan
        add_plan("待办A")
        add_plan("待办B")
        p3 = add_plan("要完成的")
        done_plan(p3.id)
        todo_plans = list_plans(status="todo")
        assert len(todo_plans) == 2
        done_plans = list_plans(status="done")
        assert len(done_plans) == 1

    def test_list_plans_by_project(self, tmp_db):
        from lingyi.plan import add_plan, list_plans
        add_plan("任务A", project="灵知")
        add_plan("任务B", project="LingFlow")
        add_plan("任务C", project="灵知")
        plans = list_plans(project="灵知")
        assert len(plans) == 2

    def test_show_plan(self, tmp_db):
        from lingyi.plan import add_plan, show_plan
        p = add_plan("可查的计划", area="研究")
        found = show_plan(p.id)
        assert found.content == "可查的计划"
        assert found.area == "研究"
        assert show_plan(999) is None

    def test_done_plan(self, tmp_db):
        from lingyi.plan import add_plan, done_plan, show_plan
        p = add_plan("要完成的任务")
        result = done_plan(p.id)
        assert result.status == "done"
        assert show_plan(p.id).status == "done"

    def test_done_plan_not_found(self, tmp_db):
        from lingyi.plan import done_plan
        assert done_plan(999) is None

    def test_cancel_plan(self, tmp_db):
        from lingyi.plan import add_plan, cancel_plan, show_plan
        p = add_plan("要取消的任务")
        assert cancel_plan(p.id) is True
        assert show_plan(p.id).status == "cancel"

    def test_cancel_plan_not_found(self, tmp_db):
        from lingyi.plan import cancel_plan
        assert cancel_plan(999) is False

    def test_plan_stats(self, tmp_db):
        from lingyi.plan import add_plan, done_plan, cancel_plan, plan_stats
        add_plan("编程A", area="编程")
        add_plan("编程B", area="编程")
        p = add_plan("编程C", area="编程")
        done_plan(p.id)
        add_plan("论文A", area="论文")
        q = add_plan("论文B", area="论文")
        cancel_plan(q.id)
        stats = plan_stats()
        assert stats["编程"]["todo"] == 2
        assert stats["编程"]["done"] == 1
        assert stats["论文"]["todo"] == 1
        assert stats["论文"]["cancel"] == 1

    def test_format_plan_short(self, tmp_db):
        from lingyi.plan import add_plan, format_plan_short
        p = add_plan("测试任务", area="编程", project="灵知")
        text = format_plan_short(p)
        assert "[1]" in text
        assert "[编程]" in text
        assert "测试任务" in text
        assert "@灵知" in text
        assert "待办" in text

    def test_format_plan_detail(self, tmp_db):
        from lingyi.plan import add_plan, format_plan_detail
        p = add_plan("详细任务", area="研究", due_date="2026-04-10", notes="重要")
        text = format_plan_detail(p)
        assert "详细任务" in text
        assert "研究" in text
        assert "2026-04-10" in text
        assert "重要" in text

    def test_format_plan_week(self, tmp_db):
        from lingyi.plan import add_plan, format_plan_week
        text = format_plan_week()
        assert "没有计划" in text

    def test_format_plan_stats(self, tmp_db):
        from lingyi.plan import format_plan_stats
        text = format_plan_stats()
        assert "暂无" in text

    def test_format_plan_stats_with_data(self, tmp_db):
        from lingyi.plan import add_plan, done_plan, format_plan_stats
        add_plan("编程A", area="编程")
        p = add_plan("编程B", area="编程")
        done_plan(p.id)
        text = format_plan_stats()
        assert "编程" in text
        assert "50%" in text

    def test_plan_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_plan.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["plan", "add", "测试计划", "--area", "编程"])
        assert r.exit_code == 0
        assert "已添加" in r.output
        r = runner.invoke(cli, ["plan", "list"])
        assert "测试计划" in r.output
        r = runner.invoke(cli, ["plan", "show", "1"])
        assert "测试计划" in r.output
        r = runner.invoke(cli, ["plan", "done", "1"])
        assert "已完成" in r.output
        r = runner.invoke(cli, ["plan", "stats"])
        assert "编程" in r.output
        r = runner.invoke(cli, ["plan", "week"])
        assert "本周计划" in r.output


# ── config 测试 ──────────────────────────────────────

class TestConfig:
    def test_load_presets(self, tmp_db):
        from lingyi.config import load_presets
        p = load_presets()
        assert "schedules" in p
        assert "projects" in p
        assert "patrol_paths" in p

    def test_load_presets_missing_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", tmp_path / "nope.json")
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        from lingyi.config import load_presets
        p = load_presets()
        assert p == {"schedules": {}, "projects": [], "patrol_paths": {}}

    def test_load_schedule_preset(self, tmp_db):
        from lingyi.config import load_schedule_preset
        clinic = load_schedule_preset("clinic")
        assert len(clinic) == 6
        assert clinic[0][0] == "Tuesday"

    def test_load_schedule_preset_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", tmp_path / "nope.json")
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        from lingyi.config import load_schedule_preset
        assert load_schedule_preset("nonexistent") == []

    def test_load_project_presets(self, tmp_db):
        from lingyi.config import load_project_presets
        projects = load_project_presets()
        assert len(projects) == 14
        names = [p["name"] for p in projects]
        assert "LingFlow" in names

    def test_load_patrol_paths(self, tmp_db):
        from lingyi.config import load_patrol_paths
        paths = load_patrol_paths()
        assert "灵依 LingYi" in paths
        assert paths["灵依 LingYi"] == "/home/ai/LingYi"


# ── patrol 测试 ──────────────────────────────────────

class TestPatrol:
    def test_check_project_no_git(self, tmp_path):
        from lingyi.patrol import check_project
        info = check_project("测试", str(tmp_path / "nogit"))
        assert info["status"] == "无git仓库"

    def test_check_project_with_git(self, tmp_path):
        import subprocess
        repo = tmp_path / "myrepo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=str(repo), capture_output=True)
        subprocess.run(["git", "-C", str(repo), "commit", "--allow-empty", "-m", "init"],
                       capture_output=True)
        from lingyi.patrol import check_project
        info = check_project("我的仓库", str(repo))
        assert info["status"] in ("有变化", "无变化")
        assert "branch" in info

    def test_generate_report_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", tmp_path / "nope.json")
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        from lingyi.patrol import generate_report
        text = generate_report()
        assert "未配置" in text

    def test_generate_report_with_path(self, tmp_db):
        from lingyi.patrol import generate_report
        text = generate_report()
        assert "灵依" in text


# ── schedule 边界测试 ──────────────────────────────

class TestScheduleBoundary:
    def test_init_ask(self, tmp_db):
        from lingyi.schedule import init_ask
        items = init_ask()
        assert len(items) == 5
        assert all(s.type == "ask" for s in items)

    def test_init_journal(self, tmp_db):
        from lingyi.schedule import init_journal
        items = init_journal()
        assert len(items) == 7
        assert all(s.type == "journal" for s in items)
        assert all("日记" in s.description for s in items)

    def test_check_journal_remind(self, tmp_db):
        from lingyi.schedule import init_journal, check_journal_remind
        init_journal()
        items = check_journal_remind()
        assert len(items) == 1

    def test_check_tomorrow_ask(self, tmp_db):
        from lingyi.schedule import init_ask, check_tomorrow_ask
        from datetime import date, timedelta
        init_ask()
        tomorrow_name = (date.today() + timedelta(days=1)).strftime("%A")
        ask_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        items = check_tomorrow_ask()
        if tomorrow_name in ask_days:
            assert len(items) > 0
        else:
            assert len(items) == 0

    def test_format_schedule(self, tmp_db):
        from lingyi.schedule import add_schedule, format_schedule
        s = add_schedule("study", "Saturday", "morning", "编程学习")
        text = format_schedule(s)
        assert "周六" in text
        assert "上午" in text
        assert "编程学习" in text

    def test_format_today_empty(self, tmp_db):
        from lingyi.schedule import format_today
        text = format_today()
        assert "没有安排" in text

    def test_format_today_with_data(self, tmp_db):
        from lingyi.schedule import init_clinic, format_today
        from datetime import date
        init_clinic()
        text = format_today()
        today_name = date.today().strftime("%A")
        clinic_days = ["Tuesday", "Wednesday", "Thursday"]
        if today_name in clinic_days:
            assert "门诊" in text or "医院" in text
        else:
            assert "没有安排" in text

    def test_format_week(self, tmp_db):
        from lingyi.schedule import init_clinic, format_week
        init_clinic()
        text = format_week()
        assert "周一" in text
        assert "周日" in text
        assert "今天" in text

    def test_schedule_cli_init_ask(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_ask.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["schedule", "init", "ask"])
        assert r.exit_code == 0
        assert "5" in r.output

    def test_schedule_cli_init_journal(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_jour.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["schedule", "init", "journal"])
        assert r.exit_code == 0
        assert "7" in r.output

    def test_schedule_cli_remind(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_rem.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        runner.invoke(cli, ["schedule", "init", "practice"])
        runner.invoke(cli, ["schedule", "init", "journal"])
        r = runner.invoke(cli, ["schedule", "remind"])
        assert r.exit_code == 0


# ── memo CLI 边界测试 ────────────────────────────────

class TestMemoCLI:
    def test_memo_show_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_ms.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        runner.invoke(cli, ["memo", "add", "可查看的备忘"])
        r = runner.invoke(cli, ["memo", "show", "1"])
        assert "可查看的备忘" in r.output
        r = runner.invoke(cli, ["memo", "show", "999"])
        assert "不存在" in r.output

    def test_memo_delete_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_md.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        runner.invoke(cli, ["memo", "add", "要删的备忘"])
        r = runner.invoke(cli, ["memo", "delete", "1"])
        assert "已删除" in r.output
        r = runner.invoke(cli, ["memo", "delete", "999"])
        assert "不存在" in r.output

    def test_memo_list_empty(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_me.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["memo", "list"])
        assert "暂无" in r.output


# ── plan 边界测试 ──────────────────────────────────

class TestPlanBoundary:
    def test_week_plans_with_data(self, tmp_db):
        from datetime import date, timedelta
        from lingyi.plan import add_plan, week_plans
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        add_plan("本周任务", due_date=monday.isoformat())
        add_plan("下周任务", due_date=(monday + timedelta(days=8)).isoformat())
        items = week_plans()
        assert len(items) == 1
        assert items[0].content == "本周任务"

    def test_plan_list_empty(self, tmp_db):
        from lingyi.plan import list_plans
        assert list_plans() == []

    def test_plan_list_order(self, tmp_db):
        from lingyi.plan import add_plan, list_plans
        add_plan("待办A")
        p = add_plan("已完成B")
        from lingyi.plan import done_plan
        done_plan(p.id)
        add_plan("待办C")
        items = list_plans()
        assert items[0].status == "todo"
        assert items[1].status == "todo"
        assert items[2].status == "done"

    def test_plan_cancel_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_pc.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        runner.invoke(cli, ["plan", "add", "取消任务"])
        r = runner.invoke(cli, ["plan", "cancel", "1"])
        assert "已取消" in r.output
        r = runner.invoke(cli, ["plan", "cancel", "999"])
        assert "不存在" in r.output

    def test_plan_list_empty_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_pe.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["plan", "list"])
        assert "暂无" in r.output

    def test_plan_show_not_found_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_pnf.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["plan", "show", "999"])
        assert "不存在" in r.output

    def test_plan_done_not_found_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_pdnf.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["plan", "done", "999"])
        assert "不存在" in r.output


# ── version 测试 ──────────────────────────────────

class TestVersion:
    def test_version_consistency(self):
        from lingyi import __version__
        assert __version__ == "0.4.0"

    def test_cli_version(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "v.db")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["--version"])
        assert "0.4.0" in r.output
