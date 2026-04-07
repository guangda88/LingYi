"""v0.1 备忘录 + v0.2 日程 + v0.3 项目 + v0.4 计划 + v0.5 记忆 + v0.6 语音 + v0.7 智能 + v0.8 连接 + v0.9 信息整理 + v0.10 编程辅助深化 + v0.11 双向语音 + v0.12 移动端 + v0.13 情报汇总 + 配置/巡检 测试。"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from lingyi.db import get_db


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
        assert "LingZhi" in names

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
        p2 = show_project("LingZhi")
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
        from lingyi.plan import format_plan_week
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
        assert paths["灵依 LingYi"] == "/home/user/LingYi"


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
        assert __version__ == "0.16.0"

    def test_cli_version(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "v.db")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["--version"])
        assert "0.16.0" in r.output


# ── v0.5 记忆：会话 ────────────────────────────────

class TestSession:
    def test_save_and_get(self, tmp_db):
        from lingyi.session import save_session, get_session
        s = save_session(summary="完成v0.5", files="session.py,pref.py",
                         decisions="用SQLite存会话", todos="v0.6语音", prefs_noted="节约token")
        assert s.id is not None
        assert s.summary == "完成v0.5"
        got = get_session(s.id)
        assert got is not None
        assert got.summary == "完成v0.5"

    def test_last_session(self, tmp_db):
        from lingyi.session import save_session, last_session
        save_session(summary="第一轮")
        save_session(summary="第二轮")
        s = last_session()
        assert s is not None
        assert s.summary == "第二轮"

    def test_last_session_empty(self, tmp_db):
        from lingyi.session import last_session
        assert last_session() is None

    def test_list_sessions(self, tmp_db):
        from lingyi.session import save_session, list_sessions
        for i in range(5):
            save_session(summary=f"会话{i}")
        sessions = list_sessions(limit=3)
        assert len(sessions) == 3
        assert sessions[0].summary == "会话4"

    def test_delete_session(self, tmp_db):
        from lingyi.session import save_session, delete_session, get_session
        s = save_session(summary="待删除")
        assert delete_session(s.id) is True
        assert get_session(s.id) is None
        assert delete_session(999) is False

    def test_format_session_detail(self, tmp_db):
        from lingyi.session import save_session, format_session_detail
        s = save_session(summary="测试", files="a.py", decisions="用Click", todos="下一步", prefs_noted="简洁")
        out = format_session_detail(s)
        assert "测试" in out
        assert "a.py" in out

    def test_format_session_resume(self, tmp_db):
        from lingyi.session import save_session, format_session_resume
        s = save_session(summary="v0.5记忆", decisions="SQLite", todos="v0.6")
        out = format_session_resume(s)
        assert "# 上次会话摘要" in out
        assert "v0.5记忆" in out

    def test_session_cli_save(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["session", "save", "--summary", "测试会话", "--files", "a.py"])
        assert "✓" in r.output

    def test_session_cli_save_empty(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["session", "save"])
        assert "至少提供" in r.output

    def test_session_cli_last_empty(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["session", "last"])
        assert "暂无" in r.output

    def test_session_cli_last_and_resume(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        runner.invoke(cli, ["session", "save", "--summary", "v0.5完成", "--todos", "v0.6"])
        r_last = runner.invoke(cli, ["session", "last"])
        assert "v0.5完成" in r_last.output
        r_resume = runner.invoke(cli, ["session", "resume"])
        assert "# 上次会话摘要" in r_resume.output

    def test_session_cli_list(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        runner.invoke(cli, ["session", "save", "--summary", "第一轮"])
        runner.invoke(cli, ["session", "save", "--summary", "第二轮"])
        r = runner.invoke(cli, ["session", "list"])
        assert "第二轮" in r.output

    def test_session_cli_show(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        runner.invoke(cli, ["session", "save", "--summary", "展示这个"])
        r = runner.invoke(cli, ["session", "show", "1"])
        assert "展示这个" in r.output
        r2 = runner.invoke(cli, ["session", "show", "999"])
        assert "不存在" in r2.output

    def test_session_cli_delete(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        runner.invoke(cli, ["session", "save", "--summary", "删除我"])
        r = runner.invoke(cli, ["session", "delete", "1"])
        assert "✓" in r.output
        r2 = runner.invoke(cli, ["session", "delete", "999"])
        assert "不存在" in r2.output


# ── v0.5 记忆：偏好 ────────────────────────────────

class TestPref:
    def test_set_and_get(self, tmp_db):
        from lingyi.pref import set_pref, get_pref
        set_pref("token_economy", "extreme")
        assert get_pref("token_economy") == "extreme"
        assert get_pref("nonexistent") is None

    def test_set_overwrites(self, tmp_db):
        from lingyi.pref import set_pref, get_pref
        set_pref("lang", "zh")
        set_pref("lang", "en")
        assert get_pref("lang") == "en"

    def test_list_prefs(self, tmp_db):
        from lingyi.pref import set_pref, list_prefs
        set_pref("a", "1")
        set_pref("b", "2")
        prefs = list_prefs()
        assert len(prefs) == 2
        assert prefs[0][0] == "a"

    def test_list_prefs_empty(self, tmp_db):
        from lingyi.pref import list_prefs
        assert list_prefs() == []

    def test_delete_pref(self, tmp_db):
        from lingyi.pref import set_pref, delete_pref, get_pref
        set_pref("temp", "val")
        assert delete_pref("temp") is True
        assert get_pref("temp") is None
        assert delete_pref("nonexistent") is False

    def test_format_pref_list(self, tmp_db):
        from lingyi.pref import format_pref_list
        assert "暂无" in format_pref_list([])
        assert "key = val" in format_pref_list([("key", "val")])

    def test_pref_cli_set_get(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["pref", "set", "style", "concise"])
        assert "✓" in r.output
        r2 = runner.invoke(cli, ["pref", "get", "style"])
        assert "concise" in r2.output

    def test_pref_cli_get_missing(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["pref", "get", "missing"])
        assert "不存在" in r.output

    def test_pref_cli_list(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        runner.invoke(cli, ["pref", "set", "a", "1"])
        runner.invoke(cli, ["pref", "set", "b", "2"])
        r = runner.invoke(cli, ["pref", "list"])
        assert "a = 1" in r.output

    def test_pref_cli_list_empty(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["pref", "list"])
        assert "暂无" in r.output

    def test_pref_cli_delete(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        runner.invoke(cli, ["pref", "set", "del_me", "val"])
        r = runner.invoke(cli, ["pref", "delete", "del_me"])
        assert "✓" in r.output
        r2 = runner.invoke(cli, ["pref", "delete", "nonexistent"])
        assert "不存在" in r2.output


# ── v0.6 语音：TTS ────────────────────────────────

class TestTTS:
    def test_clean_text(self):
        from lingyi.tts import clean_text_for_speech
        assert clean_text_for_speech("") == ""
        assert "完成" in clean_text_for_speech("✓ 完成")
        assert clean_text_for_speech("## 标题") == "标题"
        assert clean_text_for_speech("  多   空  格  ") == "多 空 格"

    def test_speak_empty(self):
        from lingyi.tts import speak
        assert speak("") is False

    def test_speak_no_player(self, monkeypatch):
        import subprocess
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("no player")))
        from lingyi.tts import speak
        assert speak("测试") is False

    def test_synthesize_to_file(self, tmp_path):
        from lingyi.tts import synthesize_to_file
        out = str(tmp_path / "test.mp3")
        result = synthesize_to_file("测试语音", out)
        assert os.path.exists(result)
        assert os.path.getsize(result) > 0


# ── v0.6 语音：chat ──────────────────────────────

class TestChat:
    def test_process_input_memo(self, tmp_db):
        from lingyi.commands.chat import _process_input
        result = _process_input("备忘买牛奶")
        assert "已记录" in result
        assert "买牛奶" in result

    def test_process_input_schedule(self, tmp_db):
        from lingyi.commands.chat import _process_input
        result = _process_input("今天有什么安排")
        assert isinstance(result, str)

    def test_process_input_help(self, tmp_db):
        from lingyi.commands.chat import _process_input
        result = _process_input("你能做什么")
        assert "日程" in result or "备忘" in result

    def test_process_input_echo(self, tmp_db):
        from lingyi.commands.chat import _process_input
        result = _process_input("随便说点什么")
        assert "收到" in result

    def test_chat_cli_quit(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["chat"], input="q\n")
        assert "再见" in r.output


# ── v0.7 智能：智能提醒 + 周报 ─────────────────────────

class TestSmartRemind:
    def test_smart_remind_basic(self, tmp_db):
        from lingyi.schedule import smart_remind
        result = smart_remind()
        assert "智能提醒" in result
        assert "建议" in result

    def test_smart_remind_with_prefs(self, tmp_db):
        from lingyi.schedule import smart_remind
        from lingyi.pref import set_pref
        set_pref("提醒_喝水", "每小时一杯")
        result = smart_remind()
        assert "偏好提醒" in result
        assert "喝水" in result

    def test_smart_remind_with_session_todos(self, tmp_db):
        from lingyi.schedule import smart_remind
        from lingyi.session import save_session
        save_session(summary="开发v0.7", todos="- 完成智能提醒\n- 完成周报")
        result = smart_remind()
        assert "上次会话待办" in result
        assert "智能提醒" in result

    def test_smart_remind_with_schedule(self, tmp_db, monkeypatch):
        from datetime import date
        from lingyi.schedule import add_schedule, smart_remind
        today_name = date.today().strftime("%A")
        add_schedule("clinic", today_name, "morning", "骨伤科门诊")
        result = smart_remind()
        assert "clinic" in result or "门诊" in result

    def test_smart_remind_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "smart.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["schedule", "remind", "--smart"])
        assert "智能提醒" in r.output


class TestWeeklyReport:
    def test_report_basic(self, tmp_db):
        from lingyi.report import generate_weekly_report
        result = generate_weekly_report()
        assert "周报" in result
        assert "计划进度" in result
        assert "活跃项目" in result

    def test_report_with_plans(self, tmp_db):
        from lingyi.report import generate_weekly_report
        from lingyi.plan import add_plan, done_plan
        p = add_plan("完成周报功能", area="编程")
        done_plan(p.id)
        result = generate_weekly_report()
        assert "50%" in result or "100%" in result

    def test_report_with_memos(self, tmp_db):
        from lingyi.report import generate_weekly_report
        from lingyi.memo import add_memo
        add_memo("v0.7开发进行中")
        result = generate_weekly_report()
        assert "v0.7" in result

    def test_report_with_session(self, tmp_db):
        from lingyi.report import generate_weekly_report
        from lingyi.session import save_session
        save_session(summary="完成v0.7智能提醒和周报")
        result = generate_weekly_report()
        assert "v0.7" in result

    def test_report_cli(self, tmp_db, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
        monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "report.db")
        monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["report"])
        assert "周报" in r.output
        assert r.exit_code == 0


# ── v0.8 连接：灵知/灵克 ─────────────────────────

class TestAskKnowledge:
    def test_ask_service_unavailable(self, monkeypatch):
        from urllib.error import URLError
        monkeypatch.setattr("lingyi.ask._request", lambda *a, **kw: (_ for _ in ()).throw(URLError("refused")))
        from lingyi.ask import ask_knowledge
        result = ask_knowledge("什么是气功")
        assert result["available"] is False
        assert "不可用" in result["answer"]

    def test_ask_success(self, monkeypatch):
        monkeypatch.setattr("lingyi.ask._request", lambda url, data=None: {
            "answer": "气功是一种传统修炼方法",
            "sources": [{"title": "气功基础", "content": "调身调息调心"}],
            "session_id": "test123",
        })
        from lingyi.ask import ask_knowledge
        result = ask_knowledge("什么是气功")
        assert result["available"] is True
        assert "气功" in result["answer"]
        assert len(result["sources"]) == 1

    def test_ask_with_category(self, monkeypatch):
        captured = {}
        def mock_request(url, data=None):
            captured["data"] = data
            captured["url"] = url
            return {"answer": "中医结果", "sources": [], "session_id": "t"}
        monkeypatch.setattr("lingyi.ask._request", mock_request)
        from lingyi.ask import ask_knowledge
        ask_knowledge("经络", category="中医")
        assert "中医" in str(captured.get("data", ""))

    def test_check_lingzhi_available(self, monkeypatch):
        monkeypatch.setattr("lingyi.ask._request", lambda url, data=None: {"status": "ok"})
        from lingyi.ask import check_lingzhi
        result = check_lingzhi()
        assert result["available"] is True

    def test_check_lingzhi_unavailable(self, monkeypatch):
        from urllib.error import URLError
        monkeypatch.setattr("lingyi.ask._request", lambda *a, **kw: (_ for _ in ()).throw(URLError("no")))
        from lingyi.ask import check_lingzhi
        result = check_lingzhi()
        assert result["available"] is False

    def test_format_ask_result_available(self):
        from lingyi.ask import format_ask_result
        data = {"available": True, "answer": "这是答案", "sources": [{"title": "T", "content": "C"}]}
        text = format_ask_result(data)
        assert "灵知回答" in text
        assert "这是答案" in text

    def test_format_ask_result_unavailable(self):
        from lingyi.ask import format_ask_result
        text = format_ask_result({"available": False, "answer": "灵知服务不可用。"})
        assert "⚠" in text

    def test_ask_medical_query_blocked(self):
        from lingyi.ask import ask_knowledge
        result = ask_knowledge("这个症状怎么治疗")
        assert result["available"] is False
        assert "医学" in result["answer"]
        assert result["sources"] == []

    def test_search_medical_query_blocked(self):
        from lingyi.ask import search_knowledge
        result = search_knowledge("感冒吃什么药")
        assert result["available"] is False
        assert result["results"] == []
        assert result["total"] == 0

    def test_ask_prescription_blocked(self):
        from lingyi.ask import ask_knowledge
        result = ask_knowledge("帮我开个处方")
        assert result["available"] is False

    def test_ask_non_medical_passes(self, monkeypatch):
        monkeypatch.setattr("lingyi.ask._request", lambda url, data=None: {
            "answer": "气功养生", "sources": [], "session_id": "t",
        })
        from lingyi.ask import ask_knowledge
        result = ask_knowledge("气功有哪些流派")
        assert result["available"] is True


class TestAskCode:
    def test_code_sdk_unavailable(self, monkeypatch):
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *a, **kw):
            if name == "lingclaude":
                raise ImportError("no sdk")
            return real_import(name, *a, **kw)
        monkeypatch.setattr(builtins, "__import__", mock_import)
        from lingyi.code import check_lingclaude
        result = check_lingclaude()
        assert result["available"] is False

    def test_code_ask_unavailable(self, monkeypatch):
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *a, **kw):
            if name == "lingclaude":
                raise ImportError("no")
            return real_import(name, *a, **kw)
        monkeypatch.setattr(builtins, "__import__", mock_import)
        from lingyi.code import ask_code
        result = ask_code("帮我检查代码")
        assert result["available"] is False

    def test_format_code_result_available(self):
        from lingyi.code import format_code_result
        data = {"available": True, "answer": "代码没有问题"}
        text = format_code_result(data)
        assert "灵克回答" in text
        assert "代码没有问题" in text

    def test_format_code_result_unavailable(self):
        from lingyi.code import format_code_result
        text = format_code_result({"available": False, "answer": "灵克不可用"})
        assert "⚠" in text


class TestConnectCLI:
    def test_ask_cli(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.ask.ask_knowledge", lambda q, **kw: {
            "answer": f"关于{q}的回答", "sources": [], "available": True,
        })
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["ask", "什么是气功"])
        assert r.exit_code == 0
        assert "灵知回答" in r.output

    def test_ask_cli_with_category(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.ask.ask_knowledge", lambda q, **kw: {
            "answer": "中医答案", "sources": [], "available": True,
        })
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["ask", "经络", "--category", "中医"])
        assert r.exit_code == 0
        assert "灵知回答" in r.output

    def test_ask_cli_unavailable(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.ask.ask_knowledge", lambda q, **kw: {
            "answer": "灵知服务不可用。", "sources": [], "available": False,
        })
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["ask", "测试"])
        assert "⚠" in r.output

    def test_code_cli(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.code.ask_code", lambda q, **kw: {
            "answer": "代码建议", "available": True,
        })
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["code", "帮我检查代码"])
        assert r.exit_code == 0
        assert "灵克回答" in r.output

    def test_code_cli_unavailable(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.code.ask_code", lambda q, **kw: {
            "answer": "灵克不可用", "available": False,
        })
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["code", "测试"])
        assert "⚠" in r.output


# ── v0.9 信息整理 ──────────────────────────────────

class TestDigest:
    def test_digest_empty(self):
        from lingyi.digest import digest_text
        result = digest_text("")
        assert result["todos"] == []
        assert result["raw_lines"] == 0

    def test_digest_todos(self):
        from lingyi.digest import digest_text
        text = "需要完成v0.9开发\n记得去买菜\n随便一行"
        result = digest_text(text)
        assert len(result["todos"]) == 2
        assert any("v0.9" in t for t in result["todos"])
        assert any("买菜" in t for t in result["todos"])

    def test_digest_decisions(self):
        from lingyi.digest import digest_text
        text = "决定用SQLite存储\n确定了方案A\n随便说说"
        result = digest_text(text)
        assert len(result["decisions"]) == 2
        assert any("SQLite" in d for d in result["decisions"])

    def test_digest_prefs(self):
        from lingyi.digest import digest_text
        text = "偏好简洁输出\n习惯用vim\n其他内容"
        result = digest_text(text)
        assert len(result["prefs"]) == 2
        assert any("简洁" in p for p in result["prefs"])

    def test_digest_facts(self):
        from lingyi.digest import digest_text
        text = "重要的是先完成核心功能\n关键在于性能优化\n普通内容"
        result = digest_text(text)
        assert len(result["facts"]) == 2
        assert any("核心功能" in f for f in result["facts"])

    def test_digest_mixed(self):
        from lingyi.digest import digest_text
        text = "需要完成开发\n决定用Python\n偏好中文界面\n重要：先做测试\n这是普通行"
        result = digest_text(text)
        assert len(result["todos"]) >= 1
        assert len(result["decisions"]) >= 1
        assert len(result["prefs"]) >= 1
        assert len(result["facts"]) >= 1
        assert result["raw_lines"] == 5

    def test_save_digest(self, tmp_db):
        from lingyi.digest import digest_text, save_digest
        data = digest_text("需要完成测试\n偏好用pytest")
        result = save_digest(data)
        assert result["memos_saved"] >= 1
        assert result["prefs_saved"] >= 1

    def test_save_digest_empty(self, tmp_db):
        from lingyi.digest import save_digest
        result = save_digest({"todos": [], "decisions": [], "prefs": [], "facts": []})
        assert result["memos_saved"] == 0
        assert result["prefs_saved"] == 0

    def test_format_digest_empty(self):
        from lingyi.digest import format_digest
        text = format_digest({"todos": [], "decisions": [], "prefs": [], "facts": [], "raw_lines": 3})
        assert "3 行" in text
        assert "未提取" in text

    def test_format_digest_with_data(self):
        from lingyi.digest import format_digest
        text = format_digest({
            "todos": ["完成任务"], "decisions": ["用Python"],
            "prefs": ["简洁"], "facts": ["性能关键"], "raw_lines": 4,
        })
        assert "待办" in text
        assert "决策" in text
        assert "偏好" in text
        assert "要点" in text

    def test_digest_cli_text(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["digest", "需要完成v0.9开发", "决定用Python"])
        assert r.exit_code == 0
        assert "待办" in r.output

    def test_digest_cli_save(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["digest", "--save", "需要完成测试任务"])
        assert r.exit_code == 0
        assert "保存" in r.output

    def test_digest_cli_file(self, tmp_db, tmp_path):
        f = tmp_path / "notes.txt"
        f.write_text("需要整理代码\n偏好简洁风格", encoding="utf-8")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["digest", "--file", str(f)])
        assert r.exit_code == 0
        assert "待办" in r.output

    def test_digest_cli_file_not_found(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["digest", "--file", "/nonexistent/file.txt"])
        assert "不存在" in r.output


# ── v0.10 编程辅助深化 ──────────────────────────────

class TestCodeReview:
    def test_review_file_not_found(self):
        from lingyi.code import review_code
        result = review_code("/nonexistent/file.py")
        assert result["available"] is False
        assert "不存在" in result["answer"]

    def test_review_not_a_file(self, tmp_path):
        from lingyi.code import review_code
        d = tmp_path / "dir"
        d.mkdir()
        result = review_code(str(d))
        assert result["available"] is False
        assert "不是文件" in result["answer"]

    def test_review_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.code._ask_engine", lambda prompt: {
            "answer": "代码质量良好", "available": True,
        })
        f = tmp_path / "test.py"
        f.write_text("def hello(): pass", encoding="utf-8")
        from lingyi.code import review_code
        result = review_code(str(f))
        assert result["available"] is True
        assert "test.py" in result["file"]

    def test_review_truncates_long_file(self, tmp_path, monkeypatch):
        captured = {}
        def mock_ask(prompt):
            captured["len"] = len(prompt)
            return {"answer": "OK", "available": True}
        monkeypatch.setattr("lingyi.code._ask_engine", mock_ask)
        f = tmp_path / "big.py"
        f.write_text("x\n" * 15000, encoding="utf-8")
        from lingyi.code import review_code
        result = review_code(str(f))
        assert result["available"] is True
        assert captured["len"] < 25000


class TestCheckDeps:
    def test_deps_project_not_found(self):
        from lingyi.code import check_dependencies
        result = check_dependencies("/nonexistent/project")
        assert result["available"] is False
        assert "不存在" in result["answer"]

    def test_deps_no_dep_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.code._ask_engine", lambda prompt: {
            "answer": "分析结果", "available": True,
        })
        from lingyi.code import check_dependencies
        result = check_dependencies(str(tmp_path))
        assert result["available"] is False
        assert "未找到" in result["answer"]

    def test_deps_with_pyproject(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.code._ask_engine", lambda prompt: {
            "answer": "依赖分析完成", "available": True,
        })
        (tmp_path / "pyproject.toml").write_text("[project]\nname='test'", encoding="utf-8")
        from lingyi.code import check_dependencies
        result = check_dependencies(str(tmp_path))
        assert result["available"] is True
        assert result["dep_file"] == "pyproject.toml"

    def test_deps_with_requirements(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.code._ask_engine", lambda prompt: {
            "answer": "依赖检查完成", "available": True,
        })
        (tmp_path / "requirements.txt").write_text("click\nedge-tts", encoding="utf-8")
        from lingyi.code import check_dependencies
        result = check_dependencies(str(tmp_path))
        assert result["available"] is True
        assert result["dep_file"] == "requirements.txt"


class TestRefactor:
    def test_refactor_file_not_found(self):
        from lingyi.code import suggest_refactor
        result = suggest_refactor("/nonexistent/file.py")
        assert result["available"] is False

    def test_refactor_success(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.code._ask_engine", lambda prompt: {
            "answer": "建议拆分函数", "available": True,
        })
        f = tmp_path / "refactor.py"
        f.write_text("def long_func(): pass", encoding="utf-8")
        from lingyi.code import suggest_refactor
        result = suggest_refactor(str(f))
        assert result["available"] is True
        assert "建议" in result["answer"]

    def test_refactor_truncates(self, tmp_path, monkeypatch):
        captured = {}
        def mock_ask(prompt):
            captured["truncated"] = "截断" in prompt
            return {"answer": "OK", "available": True}
        monkeypatch.setattr("lingyi.code._ask_engine", mock_ask)
        f = tmp_path / "big.py"
        f.write_text("x\n" * 15000, encoding="utf-8")
        from lingyi.code import suggest_refactor
        result = suggest_refactor(str(f))
        assert result["available"] is True
        assert captured["truncated"] is True


class TestCodeCLI:
    def test_review_cli(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.code.review_code", lambda fp: {
            "answer": "代码审查通过", "available": True, "file": fp,
        })
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["review", "test.py"])
        assert r.exit_code == 0
        assert "灵克回答" in r.output

    def test_deps_cli(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.code.check_dependencies", lambda pp: {
            "answer": "依赖正常", "available": True, "project": pp, "dep_file": "pyproject.toml",
        })
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["deps", "/home/ai/LingYi"])
        assert r.exit_code == 0
        assert "灵克回答" in r.output

    def test_refactor_cli(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.code.suggest_refactor", lambda fp: {
            "answer": "建议重构", "available": True, "file": fp,
        })
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["refactor", "test.py"])
        assert r.exit_code == 0
        assert "灵克回答" in r.output


# ── v0.11 双向语音 ──────────────────────────────────

class TestSTT:
    def test_check_stt_no_backend(self, monkeypatch):
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *a, **kw):
            if name in ("whisper", "sherpa_onnx"):
                raise ImportError("no")
            return real_import(name, *a, **kw)
        monkeypatch.setattr(builtins, "__import__", mock_import)
        from lingyi.stt import check_stt
        result = check_stt()
        assert result["available"] is False
        assert result["backends"] == []

    def test_transcribe_file_not_found(self):
        from lingyi.stt import transcribe_file
        result = transcribe_file("/nonexistent.wav")
        assert result["available"] is False
        assert "不存在" in result["error"]

    def test_transcribe_no_backend(self, monkeypatch):
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *a, **kw):
            if name in ("whisper", "sherpa_onnx"):
                raise ImportError("no")
            return real_import(name, *a, **kw)
        monkeypatch.setattr(builtins, "__import__", mock_import)
        from lingyi.stt import transcribe_file
        f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        f.write(b"fake audio")
        f.close()
        result = transcribe_file(f.name)
        assert result["available"] is False
        import os
        os.unlink(f.name)

    def test_format_stt_status_unavailable(self):
        from lingyi.stt import format_stt_status
        text = format_stt_status({"available": False, "backends": [], "default": None})
        assert "不可用" in text

    def test_format_stt_status_available(self):
        from lingyi.stt import format_stt_status
        text = format_stt_status({
            "available": True, "default": "whisper",
            "backends": [{"name": "whisper", "version": "1.0"}],
        })
        assert "可用" in text
        assert "whisper" in text

    def test_format_transcribe_success(self):
        from lingyi.stt import format_transcribe_result
        text = format_transcribe_result({"text": "你好", "available": True, "backend": "whisper"})
        assert "你好" in text

    def test_format_transcribe_empty(self):
        from lingyi.stt import format_transcribe_result
        text = format_transcribe_result({"text": "", "available": True, "backend": "whisper"})
        assert "未识别" in text

    def test_format_transcribe_fail(self):
        from lingyi.stt import format_transcribe_result
        text = format_transcribe_result({"text": "", "available": False, "backend": None, "error": "失败"})
        assert "失败" in text

    def test_record_audio_no_arecord(self, monkeypatch):
        import subprocess
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("no")))
        from lingyi.stt import record_audio
        result = record_audio(duration=1)
        assert result is None


class TestVoiceCLI:
    def test_stt_status_cli(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["stt-status"])
        assert r.exit_code == 0
        assert ("可用" in r.output or "不可用" in r.output)

    def test_stt_cli_no_backend(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.stt.check_stt", lambda: {
            "available": False, "backends": [], "default": None,
        })
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["stt"])
        assert "不可用" in r.output


# ── v0.12 移动端适配 ──────────────────────────────

class TestMobile:
    def test_detect_environment(self):
        from lingyi.mobile import detect_environment
        env = detect_environment()
        assert env["type"] in ("desktop", "termux", "android")
        assert isinstance(env["term_width"], int)
        assert isinstance(env["is_compact"], bool)

    def test_compact_output_short(self):
        from lingyi.mobile import compact_output
        text = "短文本"
        assert compact_output(text, width=50) == "短文本"

    def test_compact_output_long(self):
        from lingyi.mobile import compact_output
        text = "这是一段很长的文本需要被截断才能在小屏幕上显示"
        result = compact_output(text, width=20)
        assert len(result) <= 20
        assert "…" in result

    def test_compact_output_zero_width(self):
        from lingyi.mobile import compact_output
        assert compact_output("任何文本", width=0) == "任何文本"

    def test_play_audio_no_player(self, monkeypatch):
        monkeypatch.setattr("lingyi.mobile.detect_environment", lambda: {
            "audio_player": None, "type": "desktop",
        })
        from lingyi.mobile import play_audio
        assert play_audio("/fake/file.mp3") is False

    def test_play_audio_file_not_found(self, monkeypatch):
        monkeypatch.setattr("lingyi.mobile.detect_environment", lambda: {
            "audio_player": "ffplay", "type": "desktop",
        })
        import subprocess
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("no")))
        from lingyi.mobile import play_audio
        assert play_audio("/fake/file.mp3", player="ffplay") is False

    def test_format_env_info(self):
        from lingyi.mobile import format_env_info
        env = {"type": "desktop", "is_termux": False, "is_compact": False,
               "term_width": 120, "audio_player": "ffplay"}
        text = format_env_info(env)
        assert "desktop" in text
        assert "120" in text
        assert "ffplay" in text

    def test_format_env_info_termux(self):
        from lingyi.mobile import format_env_info
        env = {"type": "termux", "is_termux": True, "is_compact": True,
               "term_width": 45, "audio_player": "termux-media-player"}
        text = format_env_info(env)
        assert "termux" in text
        assert "紧凑" in text
        assert "已启用" in text

    def test_detect_audio_player_none(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: None)
        from lingyi.mobile import _detect_audio_player
        assert _detect_audio_player() is None

    def test_detect_audio_player_found(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/mpv" if name == "mpv" else None)
        from lingyi.mobile import _detect_audio_player
        assert _detect_audio_player() == "mpv"


class TestMobileCLI:
    def test_env_cli(self, tmp_db):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["env"])
        assert r.exit_code == 0
        assert "环境信息" in r.output


# ── v0.13 情报汇总 ──────────────────────────────────

class TestBriefing:
    def test_collect_lingzhi_available(self, monkeypatch):
        import json
        class MockResp:
            def read(self):
                return json.dumps({
                    "status": "ok", "version": "1.0.0",
                    "categories": ["气功", "中医"],
                    "stats": {"total": 100, "errors": 2},
                }).encode()
        monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: MockResp())
        from lingyi.briefing import collect_lingzhi
        result = collect_lingzhi()
        assert result["available"] is True
        assert result["total_queries"] == 100
        assert result["errors"] == 2
        assert result["version"] == "1.0.0"

    def test_collect_lingzhi_unavailable(self, monkeypatch):
        from urllib.error import URLError
        monkeypatch.setattr("urllib.request.urlopen",
            lambda *a, **kw: (_ for _ in ()).throw(URLError("refused")))
        from lingyi.briefing import collect_lingzhi
        result = collect_lingzhi()
        assert result["available"] is False

    def test_collect_lingflow_with_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.briefing._LINGFLOW_PATH", tmp_path)
        fb_dir = tmp_path / ".lingflow" / "feedback"
        fb_dir.mkdir(parents=True)
        fb_file = fb_dir / "feedbacks.json"
        fb_file.write_text('[{"status": "open"}, {"status": "closed"}]', encoding="utf-8")
        trends_dir = tmp_path / ".lingflow" / "reports" / "github_trends"
        trends_dir.mkdir(parents=True)
        (trends_dir / "t1.json").write_text("{}", encoding="utf-8")
        from lingyi.briefing import collect_lingflow
        result = collect_lingflow()
        assert result["available"] is True
        assert result["feedback_count"] == 2
        assert result["feedback_open"] == 1
        assert result["github_trends"] == 1

    def test_collect_lingflow_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.briefing._LINGFLOW_PATH", tmp_path)
        from lingyi.briefing import collect_lingflow
        result = collect_lingflow()
        assert result["available"] is True
        assert result["feedback_count"] == 0
        assert result["github_trends"] == 0

    def test_collect_lingclaude_no_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.briefing._LINGCLAUDE_PATH", tmp_path)
        from lingyi.briefing import collect_lingclaude
        result = collect_lingclaude()
        assert result["available"] is True
        assert result["sessions"] == 0

    def test_collect_lingclaude_with_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.briefing._LINGCLAUDE_PATH", tmp_path)
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        sessions = [{"query": "test query", "timestamp": "2026-04-03"}]
        (data_dir / "session_history.json").write_text(
            json.dumps(sessions), encoding="utf-8")
        from lingyi.briefing import collect_lingclaude
        result = collect_lingclaude()
        assert result["available"] is True
        assert result["sessions"] == 1
        assert len(result["recent_queries"]) == 1

    def test_format_briefing_full(self):
        from lingyi.briefing import format_briefing
        data = {
            "timestamp": "2026-04-03T12:00:00",
            "lingzhi": {"available": True, "version": "1.0", "categories": ["中医"],
                         "total_queries": 50, "errors": 1},
            "lingflow": {"available": True, "feedback_count": 3, "feedback_open": 1,
                          "github_trends": 2, "optimization_reports": 5, "audits": []},
            "lingclaude": {"available": True, "sessions": 10,
                           "recent_queries": [{"query": "test", "timestamp": ""}]},
        }
        text = format_briefing(data)
        assert "灵知" in text
        assert "灵通" in text
        assert "灵克" in text
        assert "50" in text

    def test_format_briefing_short(self):
        from lingyi.briefing import format_briefing_short
        data = {
            "lingzhi": {"available": True, "total_queries": 100},
            "lingflow": {"available": True, "feedback_count": 5, "feedback_open": 2},
            "lingclaude": {"available": True, "sessions": 3},
        }
        text = format_briefing_short(data)
        assert "灵知" in text
        assert "灵通" in text
        assert "灵克" in text
        assert "100" in text

    def test_format_briefing_all_unavailable(self):
        from lingyi.briefing import format_briefing
        data = {
            "timestamp": "2026-04-03T12:00:00",
            "lingzhi": {"available": False},
            "lingflow": {"available": False},
            "lingclaude": {"available": False},
        }
        text = format_briefing(data)
        assert "不可用" in text


class TestBriefingCLI:
    def test_briefing_cli_full(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.briefing.collect_lingzhi",
            lambda: {"available": False})
        monkeypatch.setattr("lingyi.briefing.collect_lingflow",
            lambda: {"available": True, "feedback_count": 0, "feedback_open": 0,
                     "github_trends": 0, "daily_reports": 0, "audits": [],
                     "optimization_reports": 0})
        monkeypatch.setattr("lingyi.briefing.collect_lingclaude",
            lambda: {"available": True, "sessions": 0, "recent_queries": []})
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["briefing"])
        assert r.exit_code == 0
        assert "灵依情报汇报" in r.output

    def test_briefing_cli_short(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.briefing.collect_lingzhi",
            lambda: {"available": True, "total_queries": 10})
        monkeypatch.setattr("lingyi.briefing.collect_lingflow",
            lambda: {"available": True, "feedback_count": 2, "feedback_open": 0,
                     "github_trends": 0, "daily_reports": 0, "audits": [],
                     "optimization_reports": 0})
        monkeypatch.setattr("lingyi.briefing.collect_lingclaude",
            lambda: {"available": True, "sessions": 5, "recent_queries": []})
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["briefing", "--short"])
        assert r.exit_code == 0
        assert "灵知" in r.output
        assert "灵通" in r.output
        assert "灵克" in r.output

    def test_briefing_cli_source(self, tmp_db, monkeypatch):
        monkeypatch.setattr("lingyi.briefing.collect_lingzhi",
            lambda: {"available": True, "version": "1.0", "categories": ["中医"],
                     "total_queries": 42, "errors": 0})
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["briefing", "--source", "lingzhi"])
        assert r.exit_code == 0
        assert "灵知" in r.output
        assert "42" in r.output


class TestDbDirect:
    def test_get_db_creates_tables(self, tmp_db):
        conn = get_db()
        tables = [row["name"] for row in
                  conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
        conn.close()
        for t in ["memos", "schedules", "projects", "plans", "sessions", "preferences"]:
            assert t in tables

    def test_get_db_wal_mode(self, tmp_db):
        conn = get_db()
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert mode == "wal"

    def test_get_db_row_factory(self, tmp_db):
        conn = get_db()
        assert conn.row_factory is not None
        conn.close()

    def test_schema_idempotent(self, tmp_db):
        conn1 = get_db()
        conn1.close()
        conn2 = get_db()
        tables = [row["name"] for row in
                  conn2.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
        conn2.close()
        assert tables.count("memos") == 1


# ── v0.14 灵信 LingMessage ──────────────────────────────

class TestLingMessage:
    def test_init_store(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store
        result = init_store()
        assert result["initialized"] is True

    def test_send_message_creates_discussion(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message
        init_store()
        msg = send_message("lingyi", "灵字辈未来", "我认为我们应该先打通知识闭环")
        assert msg.from_id == "lingyi"
        assert msg.from_name == "灵依"
        assert msg.topic == "灵字辈未来"
        assert "知识闭环" in msg.content
        assert msg.id.startswith("msg_")

    def test_send_message_appends_to_existing(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message, list_discussions
        init_store()
        send_message("lingyi", "测试话题", "第一条消息")
        send_message("lingflow", "测试话题", "第二条消息")
        discussions = list_discussions()
        assert len(discussions) == 1
        assert discussions[0]["message_count"] == 2
        assert "灵依" in discussions[0]["participants"]
        assert "灵通" in discussions[0]["participants"]

    def test_list_discussions_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import list_discussions
        result = list_discussions()
        assert result == []

    def test_list_discussions_by_status(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message, list_discussions, close_discussion
        init_store()
        send_message("lingyi", "开放话题", "讨论中")
        discussions = list_discussions(status="open")
        assert len(discussions) == 1
        disc_id = discussions[0]["id"]
        close_discussion(disc_id)
        assert len(list_discussions(status="open")) == 0
        assert len(list_discussions(status="closed")) == 1

    def test_read_discussion(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message, read_discussion
        init_store()
        send_message("lingyi", "读取测试", "内容")
        discussions = send_message("lingflow", "读取测试", "回复")
        from lingyi.lingmessage import list_discussions
        disc_list = list_discussions()
        disc_id = disc_list[0]["id"]
        disc = read_discussion(disc_id)
        assert disc is not None
        assert disc["topic"] == "读取测试"
        assert len(disc["messages"]) == 2

    def test_read_discussion_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import read_discussion
        assert read_discussion("disc_nonexistent") is None

    def test_reply_to_discussion(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message, list_discussions, reply_to_discussion
        init_store()
        send_message("lingyi", "回复测试", "原始消息")
        disc_id = list_discussions()[0]["id"]
        msg = reply_to_discussion(disc_id, "lingclaude", "灵克的回复")
        assert msg is not None
        assert msg.from_id == "lingclaude"
        assert msg.from_name == "灵克"
        assert "回复" in msg.content

    def test_reply_to_closed_discussion(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message, list_discussions, close_discussion, reply_to_discussion
        init_store()
        send_message("lingyi", "关闭测试", "消息")
        disc_id = list_discussions()[0]["id"]
        close_discussion(disc_id)
        result = reply_to_discussion(disc_id, "lingflow", "尝试回复")
        assert result is None

    def test_close_discussion(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message, list_discussions, close_discussion
        init_store()
        send_message("lingyi", "关闭话题", "消息")
        disc_id = list_discussions()[0]["id"]
        assert close_discussion(disc_id) is True
        assert close_discussion("disc_nonexistent") is False

    def test_search_messages(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message, search_messages
        init_store()
        send_message("lingyi", "搜索测试", "知识闭环是灵字辈的核心方向")
        send_message("lingflow", "搜索测试", "工程优化也很重要")
        results = search_messages("知识闭环")
        assert len(results) == 1
        assert "知识闭环" in results[0]["content"]
        results_empty = search_messages("不存在的内容")
        assert len(results_empty) == 0

    def test_format_discussion_list_empty(self):
        from lingyi.lingmessage import format_discussion_list
        text = format_discussion_list([])
        assert "暂无" in text

    def test_format_discussion_list_with_data(self):
        from lingyi.lingmessage import format_discussion_list
        discussions = [{
            "id": "disc_test",
            "topic": "测试话题",
            "participants": ["灵依", "灵通"],
            "message_count": 3,
            "status": "open",
            "updated_at": "2026-04-03T14:00:00",
        }]
        text = format_discussion_list(discussions)
        assert "测试话题" in text
        assert "灵依" in text
        assert "灵通" in text

    def test_format_discussion_thread(self):
        from lingyi.lingmessage import format_discussion_thread
        disc = {
            "id": "disc_test",
            "topic": "测试讨论",
            "initiator": "lingyi",
            "initiator_name": "灵依",
            "created_at": "2026-04-03T14:00:00",
            "participants": ["灵依"],
            "status": "open",
            "messages": [
                {"from_name": "灵依", "timestamp": "2026-04-03T14:00:00",
                 "content": "原始消息", "reply_to": None, "tags": ["战略"]},
            ],
        }
        text = format_discussion_thread(disc)
        assert "测试讨论" in text
        assert "灵依" in text
        assert "原始消息" in text

    def test_format_discussion_thread_not_found(self):
        from lingyi.lingmessage import format_discussion_thread
        assert "不存在" in format_discussion_thread(None)

    def test_send_with_tags(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message, list_discussions, read_discussion
        init_store()
        send_message("lingyi", "标签测试", "带标签的消息", tags=["战略", "v0.14"])
        disc_id = list_discussions()[0]["id"]
        disc = read_discussion(disc_id)
        assert disc["messages"][0]["tags"] == ["战略", "v0.14"]


class TestLingMessageCLI:
    def test_msg_send_cli(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-send", "--from", "lingyi", "--topic", "CLI测试", "消息内容"])
        assert r.exit_code == 0
        assert "已发送" in r.output

    def test_msg_send_invalid_project(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-send", "--from", "invalid", "--topic", "测试", "消息"])
        assert "未知项目" in r.output

    def test_msg_list_cli_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-list"])
        assert r.exit_code == 0
        assert "暂无" in r.output

    def test_msg_list_cli_with_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message
        init_store()
        send_message("lingyi", "CLI列表测试", "测试消息")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-list"])
        assert r.exit_code == 0
        assert "CLI列表测试" in r.output

    def test_msg_read_cli(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message, list_discussions
        init_store()
        send_message("lingyi", "CLI读取测试", "消息内容")
        disc_id = list_discussions()[0]["id"]
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-read", disc_id])
        assert r.exit_code == 0
        assert "CLI读取测试" in r.output

    def test_msg_read_cli_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-read", "disc_nonexistent"])
        assert "不存在" in r.output

    def test_msg_reply_cli(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message, list_discussions
        init_store()
        send_message("lingyi", "CLI回复测试", "原始")
        disc_id = list_discussions()[0]["id"]
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-reply", disc_id, "--from", "lingflow", "灵通的回复"])
        assert r.exit_code == 0
        assert "回复已发送" in r.output

    def test_msg_discuss_cli(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-discuss", "--from", "lingclaude", "新讨论", "灵克发起"])
        assert r.exit_code == 0
        assert "发起" in r.output

    def test_msg_search_cli(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message
        init_store()
        send_message("lingyi", "搜索CLI测试", "知识闭环很重要")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-search", "知识闭环"])
        assert r.exit_code == 0
        assert "知识闭环" in r.output

    def test_msg_search_cli_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store
        init_store()
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-search", "不存在"])
        assert "未找到" in r.output

    def test_msg_close_cli(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from lingyi.lingmessage import init_store, send_message, list_discussions
        init_store()
        send_message("lingyi", "CLI关闭测试", "消息")
        disc_id = list_discussions()[0]["id"]
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-close", disc_id])
        assert r.exit_code == 0
        assert "已关闭" in r.output

    def test_msg_close_cli_not_found(self, tmp_path, monkeypatch):
        monkeypatch.setattr("lingyi.lingmessage._STORE_DIR", tmp_path / "lm")
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["msg-close", "disc_nonexistent"])
        assert "不存在" in r.output


# ── v0.15 语音通话 ────────────────────────────────────

class TestVoiceCall:
    def test_check_dependencies(self):
        from lingyi.voicecall import check_voice_call
        deps = check_voice_call()
        assert "vad" in deps
        assert "stt" in deps
        assert "tts" in deps
        assert "record" in deps

    def test_format_status_all_ok(self):
        from lingyi.voicecall import format_voice_call_status
        deps = {"vad": True, "stt": True, "tts": True, "record": True}
        output = format_voice_call_status(deps)
        assert "就绪" in output
        assert "✅" in output

    def test_format_status_missing(self):
        from lingyi.voicecall import format_voice_call_status
        deps = {"vad": True, "stt": False, "tts": True, "record": False}
        output = format_voice_call_status(deps)
        assert "缺失" in output
        assert "❌" in output

    def test_generate_reply_schedule(self, tmp_db):
        from lingyi import voicecall as vc
        orig = vc._chat_llm
        vc._chat_llm = lambda conv: "今天没有安排"
        try:
            reply = vc._generate_reply("今天有什么安排", [])
            assert isinstance(reply, str)
            assert len(reply) > 0
        finally:
            vc._chat_llm = orig

    def test_generate_reply_help(self, tmp_db):
        from lingyi import voicecall as vc
        orig = vc._chat_llm
        vc._chat_llm = lambda conv: "我是灵依，你的AI助理"
        try:
            reply = vc._generate_reply("你能做什么", [])
            assert "灵依" in reply
        finally:
            vc._chat_llm = orig

    def test_generate_reply_goodbye(self, tmp_db):
        from lingyi.voicecall import _generate_reply
        reply = _generate_reply("再见", [])
        assert "再见" in reply

    def test_generate_reply_memo(self, tmp_db):
        from lingyi.voicecall import _generate_reply
        reply = _generate_reply("备忘买牛奶", [])
        assert "已记录" in reply

    def test_generate_reply_fallback(self, tmp_db):
        from lingyi import voicecall as vc
        orig = vc._chat_llm
        vc._chat_llm = lambda conv: "你好呀"
        try:
            reply = vc._generate_reply("你好呀", [])
            assert isinstance(reply, str)
        finally:
            vc._chat_llm = orig

    def test_call_status_cli(self):
        from click.testing import CliRunner
        from lingyi.cli import cli
        runner = CliRunner()
        r = runner.invoke(cli, ["call-status"])
        assert r.exit_code == 0
        assert "语音通话" in r.output
