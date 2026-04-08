# AGENTS.md — LingYi (灵依) Codebase Guide

> **灵依 LingYi** — A private AI assistant (CLI-first). Manages schedules, memos, projects, plans, sessions, preferences, TTS/STT voice I/O, smart reminders, weekly reports, knowledge retrieval, code assistance, content digestion, mobile support, briefing summaries, and cross-project discussions. Current version: **v0.14.0**.

---

## Project Overview

- **Language**: Python 3.12
- **Framework**: Click (CLI)
- **Database**: SQLite (stored at `~/.lingyi/lingyi.db`)
- **User Config**: `~/.lingyi/presets.json` (private, not in git)
- **TTS Engine**: edge-tts (Microsoft, free)
- **STT Engine**: Whisper (OpenAI, local)
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
lingyi ask "什么是气功"
lingyi code "写一个排序函数"
lingyi digest ~/notes.txt
lingyi briefing
lingyi msg-list
lingyi msg-read disc_20260404021153
lingyi msg-send --from lingyi --topic "灵字辈大家庭的未来发展方向" "我提议以知识闭环为第一优先"
lingyi stt recording.wav

# Run tests
pytest                          # All tests (configured via pyproject.toml, testpaths=["tests"])
pytest tests/test_basic.py      # Specific test file
pytest -x                       # Stop on first failure
pytest -k TestMemo              # Run specific test class
```

---

## Project Structure

```
LingYi/
├── src/lingyi/                  # Main package
│   ├── __init__.py              # Version (0.14.0)
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
│   ├── tts.py                   # TTS via edge-tts + ffplay playback (v0.6)
│   ├── stt.py                   # STT via Whisper for transcription (v0.11)
│   ├── patrol.py                # Git-based project patrol/reporting
│   ├── ask.py                   # 灵知 REST API client with medical query guardrail (v0.8)
│   ├── code.py                  # 灵克 LingClaude code assistance client (v0.10)
│   ├── digest.py                # Content digestion and summarization (v0.9)
│   ├── briefing.py              # Daily briefing aggregation (v0.13)
│   ├── lingmessage.py           # Cross-project discussion framework (v0.14)
│   ├── mobile.py                # Mobile device support (v0.12)
│   └── commands/                # CLI subcommand modules (one file per domain)
│       ├── __init__.py
│       ├── memo.py              #   Memo CLI commands
│       ├── schedule.py          #   Schedule CLI commands (includes remind --smart)
│       ├── project.py           #   Project CLI commands
│       ├── plan.py              #   Plan CLI commands
│       ├── session.py           #   Session CLI commands
│       ├── pref.py              #   Preference CLI commands
│       ├── chat.py              #   Interactive chat mode (v0.6)
│       ├── connect.py           #   Ask/Code CLI commands (v0.8)
│       ├── digest.py            #   Digest CLI commands (v0.9)
│       ├── briefing.py          #   Briefing CLI commands (v0.13)
│       ├── lingmessage.py       #   LingMessage CLI commands (v0.14)
│       ├── voice.py             #   Voice I/O CLI commands (v0.11)
│       └── mobile.py            #   Mobile CLI commands (v0.12)
├── tests/
│   ├── __init__.py
│   ├── test_basic.py            # All tests in one file (243 tests)
│   └── test_presets.json        # Test fixture presets data
├── docs/                        # Documentation
│   ├── MISSION.md               # Charter, values, boundaries
│   ├── DEVELOPMENT_PRINCIPLES.md# 10 development principles
│   ├── DEVELOPMENT_PLAN.md      # Version roadmap (v0.1–v0.14+)
│   ├── PRD.md                   # Product requirements
│   ├── USER_PROFILE.md          # User profile
│   ├── AUDIT_REPORT_v0.13.md   # v0.13 audit report
│   ├── LINGMESSAGE_RFC.md      # LingMessage RFC design doc (v0.14)
│   └── LINGMESSAGE_DISCUSSIONS.md # First batch discussion summary (v0.14)
├── presets.example.json         # Template for user config (committed)
├── pyproject.toml               # Build config, dependencies, pytest config
└── .lingflow/                   # LingFlow workspace (gitignored)
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

### External Service Pattern

- **ask.py**: REST API client for 灵知 (knowledge base) via `urllib`. Medical query guardrail via `_is_medical_query()`.
- **code.py**: Client for 灵克 LingClaude (code assistance). Graceful fallback when SDK unavailable.
- **briefing.py**: Aggregates data from multiple services. Each external call wrapped in try/except with graceful degradation.

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

- **Single test file**: `tests/test_basic.py` contains all 211 tests
- **Fixture `tmp_db`**: Creates temp DB via `monkeypatch` on `lingyi.db.DB_DIR` and `lingyi.db.DB_PATH`, patches `lingyi.config.PRESETS_PATH` to `tests/test_presets.json`
- **Test categories**: Unit tests per domain (Memo, Schedule, Project, Plan, Session, Pref, TTS, STT, Chat, SmartRemind, WeeklyReport, AskKnowledge, AskCode, Digest, Briefing, Mobile, Voice, LingMessage) + CLI integration tests
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
- `~/.lingyi/presets.json` contains real schedule data and is gitignored
- `presets.example.json` is the template with placeholder data
- Tests use `tests/test_presets.json` with test data

### Schedule Day Names
- Days stored as full English names: `"Monday"`, `"Tuesday"`, etc.
- Display uses Chinese: `周一`, `周二`, etc. (mapped via `_DAY_CN` dict)
- Time slots: `"morning"`, `"afternoon"`, `"evening"` → `上午`, `下午`, `晚上`

### Plan Areas (Five Domains)
- `医疗`, `编程`, `研究`, `论文`, `学术`
- Default area is `编程`

### Medical Query Guardrail (v0.8+)
- `ask.py` blocks medical queries (诊断/辨证/方剂/处方/怎么治/吃什么药/治疗方案)
- Charter principle: "不碰医学知识检索" — over-blocking is intentional
- `connect.py` CLI does not list `中医` as a category

### Project Lookup
- `show_project()` and `update_project()` accept **name OR alias** (case-insensitive via `COLLATE NOCASE`)
- e.g., `lingyi project show 灵通` finds `LingFlow`

### Init Idempotency
- `schedule init <preset>` and `project init` check if data already exists before inserting — safe to run multiple times

### TTS/STT Dependencies
- `edge-tts` is a runtime dependency
- `ffplay` (from ffmpeg) is needed for actual audio playback — `speak()` silently returns `False` if unavailable
- `whisper` is needed for STT — `transcribe()` gracefully degrades if unavailable
- `synthesize_to_file()` writes MP3 without needing ffplay

### Chat Mode
- `lingyi chat` is a keyword-based interactive loop
- Keyword matching: "今天/日程/安排" → schedule, "备忘/记一下/提醒我" → memo, etc.

### DB Connection Handling
- No connection pooling — each function opens and closes its own connection
- No ORM — raw SQL with parameterized queries

### Smart Remind (v0.7)
- `schedule remind --smart` uses `smart_remind()` in `schedule.py`
- Combines: today's schedule + user preferences + last session's todos
- Generates contextual suggestions

### Weekly Report (v0.7)
- `lingyi report` uses `report.py` module
- Aggregates: week schedule + plan stats + recent memos + active projects + recent sessions

### Briefing (v0.13)
- `lingyi briefing` aggregates: weather + schedule + tasks + project status + recent memos
- Each external call wrapped in try/except — graceful degradation when services unavailable

### LingMessage (v0.14)
- `lingyi msg-send/msg-list/msg-read/msg-reply/msg-search/msg-close` — cross-project discussion commands
- File-based storage at `/home/ai/.lingmessage/` (outside project DB, cross-project scope)
- Topic-based threading: `send_message()` auto-groups messages by matching open topic
- 9 project identities in `PROJECTS` dict — each message records `from_id` (English) and `from_name` (Chinese)
- `list_discussions()` returns lightweight index entries; use `read_discussion()` for full thread data
- Message IDs are timestamp-based (`msg_YYYYMMDDHHMMSS`) — not collision-proof for rapid sequential calls

### Data Truth Principle (v0.16)
- **Rule**: Any UI field must pass the Data Truth Check: (1) Where does the data come from? (2) Who updates it?
- **Anti-pattern**: "Data Hallucination" — a field defined, stored, and displayed while never updated by any code (e.g., `energy_pct` was a phantom field)
- **Principle**: Empty is honest; fake numbers are deception. Better to show nothing than a dead number.

---

## Key Documentation

| File | Purpose |
|------|---------|
| `docs/MISSION.md` | Charter — mission, values (prioritized), boundaries, related projects |
| `docs/DEVELOPMENT_PRINCIPLES.md` | 10 development principles — the "rules of the road" |
| `docs/DEVELOPMENT_PLAN.md` | Version roadmap v0.1–v0.14+ with estimates |
| `docs/PRD.md` | Product requirements document |
| `docs/USER_PROFILE.md` | User profile context |
| `docs/AUDIT_REPORT_v0.13.md` | v0.13 audit against charter and principles |

### Core Values (Priority Order)
1. **守界** (Boundaries) — Don't cross into medical diagnosis, don't make decisions for the user
2. **惜时** (Time-saving) — Direct answers, no filler
3. **节约** (Economy) — Every token counts, minimize API calls
4. **知己** (Know the user) — Remember habits, accumulate preferences
5. **可靠** (Reliability) — Only say what you can do, never fabricate

### Related Projects
- **灵通 LingFlow** — Multi-agent workflow engine at `/home/ai/LingFlow` (v3.8.0), used as development tool
- **灵知系统** — Knowledge base with REST API (integrated since v0.8)
- **灵克 LingClaude** — Local AI coding model at `/home/ai/LingClaude`
- **智桥 Zhineng-Bridge** — Relay service at port 8080 bridging LingYi to LingZhi

### Port Mapping
- **8000**: 灵知 (LingZhi) — FastAPI knowledge system
- **8080**: 智桥 (Zhineng-Bridge) — Relay/bridge service

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
| v0.8 | 连接 (Connect) | 灵知 REST API integration, medical query guardrail |
| v0.9 | 信息整理 (Digest) | Content digestion, summarization, file ingestion |
| v0.10 | 编程辅助深化 | Code assistance via 灵克, code review, refactoring |
| v0.11 | 双向语音 | STT via Whisper, voice CLI commands |
| v0.12 | 移动端 | Mobile device support, remote access |
| v0.13 | 情报汇总 (Briefing) | Daily briefing aggregation, multi-source summary |

**Next up**: v0.14+ — see DEVELOPMENT_PLAN.md for roadmap

---

## ⚡ 当前待办任务 (来自灵知 2026-04-08)

**灵信线程 #329 — 项目统计汇总**

### 任务1: MCP封装评估报告统计
读取 `/home/ai/zhineng-knowledge-system/docs/reports/MCP_ENCAPSULATION_ASSESSMENT.md`，提取关键数据：
- 73项工具的 P0/P1/P2 分布
- 各层级工具数量
- 已完成 vs 待开发的 P0 项

### 任务2: 训练数据流水线统计
读取 `/home/ai/zhineng-knowledge-system/data/training/pipeline_report.json`，汇总：
- 数据源分布 (documents/guji_documents/textbook_knowledge)
- 各数据集样本数 (intent/embedding/qa)
- 流水线性能 (耗时、优化效果)

### 任务3: 生成汇总报告
整合以上数据，生成结构化统计报告。完成后在 lingmessage 线程 #329 回复灵知 (lingzhi)。
