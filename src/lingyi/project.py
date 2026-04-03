"""项目管理：14个项目录入、状态看板、优先级。"""

from .db import get_db
from .models import Project

_STATUS_ORDER = {"active": 0, "maintenance": 1, "paused": 2, "archived": 3}
_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

_STATUS_CN = {
    "active": "活跃", "maintenance": "维护", "paused": "暂停", "archived": "归档",
}
_PRIORITY_CN = {"P0": "紧急", "P1": "高", "P2": "中", "P3": "低"}
_CATEGORY_CN = {
    "core": "核心框架", "knowledge": "知识系统", "tool": "工具生态",
    "content": "内容生成", "research": "AI研究", "infra": "基础设施", "app": "应用层",
}

_PROJECTS_DATA = [
    {"name": "LingFlow", "alias": "灵通", "status": "active", "priority": "P0",
     "category": "core", "description": "多智能体协作工程流平台",
     "repo": "LingFlow", "version": "v3.8.0", "energy_pct": 25},
    {"name": "LingClaude", "alias": "灵克", "status": "active", "priority": "P0",
     "category": "core", "description": "本地AM自学习模型，编程能力核心",
     "repo": "LingClaude", "version": "v0.2.0", "energy_pct": 25},
    {"name": "灵知系统", "alias": "灵知", "status": "active", "priority": "P0",
     "category": "knowledge", "description": "10域RAG知识库（儒释道医武哲科气心理+心理学）",
     "repo": "zhineng-knowledge-system", "version": "v1.3.0", "energy_pct": 25},
    {"name": "LingYi", "alias": "灵依", "status": "active", "priority": "P1",
     "category": "app", "description": "私我AI助理",
     "repo": "LingYi", "version": "v0.2.0", "energy_pct": 10},
    {"name": "lingtongask", "alias": "灵通问道", "status": "active", "priority": "P2",
     "category": "content", "description": "AI气功播客，每周5更",
     "repo": "lingtongask", "version": "v0.1.0", "energy_pct": 5},
    {"name": "Ling-term-mcp", "alias": "灵犀", "status": "maintenance", "priority": "P2",
     "category": "tool", "description": "MCP终端服务器",
     "repo": "Ling-term-mcp", "version": "v1.0.0", "energy_pct": 0},
    {"name": "LingMinOpt", "alias": "灵极优", "status": "maintenance", "priority": "P3",
     "category": "tool", "description": "通用自优化框架",
     "repo": "LingMinOpt", "version": "v0.1.0", "energy_pct": 0},
    {"name": "zhineng-bridge", "alias": "智桥", "status": "paused", "priority": "P3",
     "category": "tool", "description": "跨设备AI编程指令同步",
     "repo": "zhineng-bridge", "version": "v1.0.0", "energy_pct": 0},
    {"name": "lingresearch", "alias": "灵研", "status": "paused", "priority": "P3",
     "category": "research", "description": "自主AI研究框架",
     "repo": "lingresearch", "version": "v0.1.0", "energy_pct": 0},
    {"name": "ai-knowledge-base", "alias": "中医知识库", "status": "archived", "priority": "P3",
     "category": "knowledge", "description": "中医知识库原始版（已被灵知取代）",
     "repo": "ai-knowledge-base", "version": "", "energy_pct": 0},
    {"name": "Knowledge-System", "alias": "IMA导出", "status": "archived", "priority": "P3",
     "category": "tool", "description": "IMA知识库导出工具（已完成使命）",
     "repo": "Knowledge-System", "version": "v1.0.0", "energy_pct": 0},
    {"name": "ai-server", "alias": "AI私服", "status": "maintenance", "priority": "P3",
     "category": "infra", "description": "ZBOX AI私服监控",
     "repo": "ai-server", "version": "", "energy_pct": 0},
    {"name": "lingflow-skills-example", "alias": "技能示例", "status": "archived", "priority": "P3",
     "category": "tool", "description": "LingFlow技能示例",
     "repo": "lingflow-skills-example", "version": "", "energy_pct": 0},
    {"name": "lingflow-skills-index", "alias": "技能市场", "status": "archived", "priority": "P3",
     "category": "tool", "description": "LingFlow技能市场索引",
     "repo": "lingflow-skills-index", "version": "", "energy_pct": 0},
]


def init_projects() -> list[Project]:
    conn = get_db()
    existing = conn.execute("SELECT id FROM projects LIMIT 1").fetchone()
    if existing:
        conn.close()
        return list_projects()
    for data in _PROJECTS_DATA:
        conn.execute(
            "INSERT INTO projects (name, alias, status, priority, category, description, repo, version, energy_pct) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (data["name"], data["alias"], data["status"], data["priority"],
             data["category"], data["description"], data["repo"], data["version"], data["energy_pct"]),
        )
    conn.commit()
    result = list_projects()
    conn.close()
    return result


def add_project(name: str, alias: str = "", status: str = "active", priority: str = "P3",
                category: str = "tool", description: str = "", repo: str = "",
                version: str = "", energy_pct: int = 0, notes: str = "") -> Project:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO projects (name, alias, status, priority, category, description, repo, version, energy_pct, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (name, alias, status, priority, category, description, repo, version, energy_pct, notes),
    )
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.commit()
    conn.close()
    return Project(**dict(row))


def list_projects(status: str | None = None, category: str | None = None) -> list[Project]:
    conn = get_db()
    sql = "SELECT * FROM projects"
    conditions: list[str] = []
    params: list = []
    if status:
        conditions.append("status = ?")
        params.append(status)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY CASE priority"
    for i, p in enumerate(["P0", "P1", "P2", "P3"]):
        sql += f" WHEN '{p}' THEN {i}"
    sql += " ELSE 4 END, name"
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [Project(**dict(r)) for r in rows]


def show_project(name_or_alias: str) -> Project | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM projects WHERE name = ? OR alias = ? COLLATE NOCASE",
        (name_or_alias, name_or_alias),
    ).fetchone()
    conn.close()
    return Project(**dict(row)) if row else None


def update_project(name_or_alias: str, **kwargs) -> Project | None:
    if not kwargs:
        return show_project(name_or_alias)
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM projects WHERE name = ? OR alias = ? COLLATE NOCASE",
        (name_or_alias, name_or_alias),
    ).fetchone()
    if not row:
        conn.close()
        return None
    project_id = row["id"]
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [project_id]
    conn.execute(f"UPDATE projects SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", vals)
    conn.commit()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return Project(**dict(row)) if row else None


def format_project_short(p: Project) -> str:
    status_cn = _STATUS_CN.get(p.status, p.status)
    priority_cn = _PRIORITY_CN.get(p.priority, p.priority)
    alias = f"（{p.alias}）" if p.alias else ""
    energy = f" [{p.energy_pct}%]" if p.energy_pct else ""
    ver = f" {p.version}" if p.version else ""
    return f"  [{p.id}] {p.name}{alias}  {status_cn}  {priority_cn}{ver}{energy}"


def format_project_detail(p: Project) -> str:
    lines = [
        f"  #{p.id} {p.name}（{p.alias}）" if p.alias else f"  #{p.id} {p.name}",
        f"  状态：{_STATUS_CN.get(p.status, p.status)}",
        f"  优先级：{_PRIORITY_CN.get(p.priority, p.priority)}",
        f"  分类：{_CATEGORY_CN.get(p.category, p.category)}",
        f"  说明：{p.description or '—'}",
        f"  仓库：{p.repo or '—'}",
        f"  版本：{p.version or '—'}",
        f"  精力分配：{p.energy_pct}%",
        f"  备注：{p.notes or '—'}",
        f"  创建：{p.created_at}",
    ]
    return "\n".join(lines)


def format_project_kanban(projects: list[Project] | None = None) -> str:
    if projects is None:
        projects = list_projects()
    if not projects:
        return "暂无项目。"

    by_status: dict[str, list[Project]] = {}
    for p in projects:
        by_status.setdefault(p.status, []).append(p)

    lines = []
    for status in ["active", "maintenance", "paused", "archived"]:
        items = by_status.get(status, [])
        if not items:
            continue
        status_cn = _STATUS_CN.get(status, status)
        lines.append(f"{'─' * 3} {status_cn}（{len(items)}）{'─' * 20}")
        for p in items:
            lines.append(format_project_short(p))
    return "\n".join(lines)
