# AGENTS.md — LingYi (灵依) Codebase Guide

> **灵依 LingYi** — A private AI assistant (CLI-first). Manages schedules, memos, projects, plans, sessions, preferences, TTS voice output, and smart reminders/reports. Current version: **v0.7.0**.

---

## Project Overview

- **Language**: Python 3.12
- **Framework**: Click (CLI)
- **Database**: SQLite (stored at `~/.lingyi/lingyi.db`)
- **User Config**: `~/.lingyi/presets.json` (private, not in git)
- **TTS Engine**: edge-tts (Microsoft, free)
- **Build System**: setuptools via `pyproject.toml`

This is a **personal tool**, not a public product. The design philosophy is: simplicity over elegance, running over perfect architecture, daily-use over feature-completeness.

---

## Essential Commands

```bash
# Install (editable mode)
pip install -e . --break-system-packages

# Run CLI
lingyi --version
lingyi memo add "hello"
lingyi schedule today
lingyi schedule remind --smart
lingyi report
lingyi patrol

# Run tests
pytest                          # All tests (configured via pyproject.toml, testpaths=["tests"])
pytest tests/test_basic.py      # Specific test file
pytest -x                       # Stop on first failure
pytest -k TestMemo              # Run specific test class

# No separate lint command observed — no linter configured in pyproject.toml
```

---

## Project Structure

```
LingYi/
├── src/lingyi/                  # Main package
│   ├── __init__.py              # Version (0.7.0)
│   ├── cli.py                   # CLI entry point — Click group + command registration
│   ├── models.py                # Dataclasses: Memo, Schedule, Project, Plan, Session
│   ├── db.py                    # SQLite connection, schema (6 tables), get_db()
│   ├── config.py                # Load ~/.lingyi/presets.json (schedules, projects, patrol paths)
│   ├── memo.py                  # Memo CRUD logic
│   ├── schedule.py              # Schedule CRUD, today/week views, reminders, smart_remind()
│   ├── project.py               # Project CRUD, kanban, lookup by name or alias
│   ├── plan.py                  # Plan CRUD, week plans, stats by area
│   ├── session.py               # Session summary CRUD (for cross-session memory)
│   ├── pref.py                  # Key-value preference persistence
│   ├── report.py                # Weekly report generation (v0.7)
│   ├── tts.py                   # TTS via edge-tts + ffplay playback
│   ├── patrol.py                # Git-based project patrol/reporting
│   └── commands/                # CLI subcommand modules (one file per domain)
│       ├── __init__.py
│       ├── memo.py              #   Memo CLI commands
│       ├── schedule.py          #   Schedule CLI commands (includes remind --smart)
│       ├── project.py           #   Project CLI commands
│       ├── plan.py              #   Plan CLI commands
│       ├── session.py           #   Session CLI commands
│       ├── pref.py              #   Preference CLI commands
│       └── chat.py              #   Interactive chat mode
├── tests/
│   ├── __init__.py
│   ├── test_basic.py            # All tests in one file (129 tests)
│   └── test_presets.json        # Test fixture presets data
├── docs/                        # Documentation
│   ├── MISSION.md               # Charter, values, boundaries
│   ├── DEVELOPMENT_PRINCIPLES.md# 10 development principles
│   ├── DEVELOPMENT_PLAN.md      # Version roadmap (v0.1–v0.9+)
│   ├── PRD.md                   # Product requirements
│   └── USER_PROFILE.md          # User profile
├── presets.example.json         # Template for user config (committed)
├── pyproject.toml               # Build config, dependencies, pytest config
└── .lingflow/                   # LingFlow workspace (logs, config, sessions)
```

---

## Architecture Pattern

### Two-Layer Design: Logic + Commands

Each domain has **two files**:

1. **Logic module** (`src/lingyi/<domain>.py`): Pure business logic — CRUD operations, formatting, queries. Imports `db.get_db()` and `models.*`.
2. **Command module** (`src/lingyi/commands/<domain>.py`): Click CLI wiring. Imports logic module. Defines `register(group: click.Group)` function that attaches subcommands.

Example:
- `src/lingyi/memo.py` → `add_memo()`, `list_memos()`, `delete_memo()`
- `src/lingyi/commands/memo.py` → `register()` adds `memo add`, `memo list`, `memo delete` commands

### CLI Registration Pattern

In `cli.py`:
```python
from .commands import memo as memo_cmds

@cli.group()
def memo():
    """备忘录"""
    pass

memo_cmds.register(memo)
```

Each command module defines a top-level `register(group)` function that uses decorators to attach commands.

### Database Pattern

- `db.get_db()` returns a new `sqlite3.Connection` each call
- Schema is applied via `CREATE TABLE IF NOT EXISTS` on every connection
- Connection uses `row_factory = sqlite3.Row` for dict-like access
- WAL mode and foreign keys enabled
- **Pattern**: open conn → execute → commit → close (no context manager)

### Data Model Pattern

All models are `@dataclass` in `models.py` with `id: int | None = None` and timestamp fields. Conversion from DB row: `Memo(**dict(row))`.

---

## Database Schema (6 tables)

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `memos` | id, content, created_at, updated_at | Simple notes |
| `schedules` | id, type, day, time_slot, description, is_active | day=Monday..Sunday, time_slot=morning/afternoon/evening |
| `projects` | id, name (UNIQUE), alias, status, priority, category, energy_pct | status: active/maintenance/paused/archived, priority: P0-P3 |
| `plans` | id, content, area, project, status, due_date | area: 医疗/编程/研究/论文/学术, status: todo/done/cancel |
| `sessions` | id, summary, files, decisions, todos, prefs_noted | Cross-session memory |
| `preferences` | key (UNIQUE), value | Key-value user preferences |

---

## Naming Conventions

- **Code (English)**: Variable names, function names, directory names, file names
- **User-facing text (Chinese)**: All CLI help strings, output messages, error messages, docstrings
- **Commit format**: `类型: 中文描述` — e.g., `feat: 添加门诊日程管理`, `fix: 修复计划排序`, `refactor: 代码拆分`
- **Commit types**: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`
- **File naming**: Lowercase English, one word per module (`memo.py`, `schedule.py`)
- **Test class naming**: `Test<Domain>` (e.g., `TestMemo`, `TestSchedule`, `TestProject`)

---

## Testing Approach

- **Single test file**: `tests/test_basic.py` contains all 129 tests
- **Fixture `tmp_db`**: Creates temp DB via `monkeypatch` on `lingyi.db.DB_DIR` and `lingyi.db.DB_PATH`, patches `lingyi.config.PRESETS_PATH` to `tests/test_presets.json`
- **Test categories**: Unit tests per domain (Memo, Schedule, Project, Plan, Session, Pref, TTS, Chat, SmartRemind, WeeklyReport) + CLI integration tests (using `click.testing.CliRunner`)
- **Test data**: `tests/test_presets.json` has simplified schedule/project/patrol data
- **Philosophy**: "核心路径有测试" — critical modules must have tests; no 100% coverage target

### Test Fixture Pattern

```python
@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
    monkeypatch.setattr("lingyi.db.DB_PATH", db_path)
    monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
    return str(db_path)
```

For CLI tests, additional monkeypatching is done to use a separate DB per test:
```python
def test_plan_cli(self, tmp_db, tmp_path, monkeypatch):
    monkeypatch.setattr("lingyi.db.DB_DIR", tmp_path)
    monkeypatch.setattr("lingyi.db.DB_PATH", tmp_path / "cli_plan.db")
    monkeypatch.setattr("lingyi.config.PRESETS_PATH", _TEST_PRESETS)
```

---

## Gotchas & Non-Obvious Patterns

### Private Config Not in Git
- `~/.lingyi/presets.json` contains real schedule data (hospital names, etc.) and is gitignored
- `presets.example.json` is the template with placeholder data
- Tests use `tests/test_presets.json` with real-ish data

### Schedule Day Names
- Days stored as full English names: `"Monday"`, `"Tuesday"`, etc.
- Display uses Chinese: `周一`, `周二`, etc. (mapped via `_DAY_CN` dict)
- Time slots: `"morning"`, `"afternoon"`, `"evening"` → `上午`, `下午`, `晚上`

### Plan Areas (Five Domains)
- `医疗`, `编程`, `研究`, `论文`, `学术`
- Default area is `编程`

### Project Lookup
- `show_project()` and `update_project()` accept **name OR alias** (case-insensitive via `COLLATE NOCASE`)
- e.g., `lingyi project show 灵通` finds `LingFlow`

### Init Idempotency
- `schedule init <preset>` and `project init` check if data already exists before inserting — safe to run multiple times

### TTS Dependency
- `edge-tts` is a runtime dependency
- `ffplay` (from ffmpeg) is needed for actual audio playback — `speak()` silently returns `False` if unavailable
- `synthesize_to_file()` writes MP3 without needing ffplay

### Chat Mode
- `lingyi chat` is a simple keyword-based interactive loop (no LLM integration yet)
- Keyword matching: "今天/日程/安排" → schedule, "备忘/记一下/提醒我" → memo, etc.

### DB Connection Handling
- No connection pooling — each function opens and closes its own connection
- No ORM — raw SQL with parameterized queries

### Smart Remind (v0.7)
- `schedule remind --smart` uses `smart_remind()` in `schedule.py`
- Combines: today's schedule + user preferences (filtered by 提醒/习惯/注意 keywords) + last session's todos
- Generates contextual suggestions (e.g., "today has clinic, prepare case files")

### Weekly Report (v0.7)
- `lingyi report` uses `report.py` module
- Aggregates: week schedule + plan stats + recent memos + active projects + recent sessions
- Plan stats show completion rate per area

---

## Key Documentation

| File | Purpose |
|------|---------|
| `docs/MISSION.md` | Charter — mission, values (prioritized), boundaries, related projects |
| `docs/DEVELOPMENT_PRINCIPLES.md` | 10 development principles — the "rules of the road" |
| `docs/DEVELOPMENT_PLAN.md` | Version roadmap v0.1–v0.9+ with estimates |
| `docs/PRD.md` | Product requirements document |
| `docs/USER_PROFILE.md` | User profile context |

### Core Values (Priority Order)
1. **守界** (Boundaries) — Don't cross into medical diagnosis, don't make decisions for the user
2. **惜时** (Time-saving) — Direct answers, no filler
3. **节约** (Economy) — Every token counts, minimize API calls
4. **知己** (Know the user) — Remember habits, accumulate preferences
5. **可靠** (Reliability) — Only say what you can do, never fabricate

### Related Projects
- **灵通 LingFlow** — Multi-agent workflow engine at `/home/ai/LingFlow` (v3.8.0), used as development tool
- **灵知系统** — Knowledge base (planned REST API integration in v0.8)
- **灵克 LingClaude** — Local AI coding model at `/home/ai/LingClaude`

---

## Version History

| Version | Theme | Key Features |
|---------|-------|-------------|
| v0.1 | 能跑 (Running) | CLI entry, SQLite, memo CRUD |
| v0.2 | 日程 (Schedule) | Clinic schedules, reminders, patrol |
| v0.3 | 项目 (Projects) | 14-project kanban, status management |
| v0.4 | 计划 (Plans) | 5-domain task tracking, week plans, stats |
| v0.5 | 记忆 (Memory) | Session summaries, preference persistence |
| v0.6 | 语音 (Voice) | TTS playback (`--speak`), interactive chat mode |
| v0.7 | 智能 (Smart) | Smart reminders (`--smart`), weekly report (`lingyi report`) |

**Next up**: v0.8 连接 (Connect) — 灵知 REST API, 灵克 integration
