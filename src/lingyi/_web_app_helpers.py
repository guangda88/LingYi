"""Web 共用辅助函数。"""

from __future__ import annotations

import subprocess
from pathlib import Path


def git_info(repo_name: str) -> dict:
    home = Path.home()
    candidates = [home / repo_name, home / "lingtongask" / repo_name, home / "LingYi" / repo_name]
    repo_dir = next((c for c in candidates if (c / ".git").is_dir()), None)
    if not repo_dir:
        return {"repo_found": False}
    try:
        def _git(*args: str) -> str:
            return subprocess.run(["git", "-C", str(repo_dir)] + list(args),
                           capture_output=True, text=True, timeout=5).stdout.strip()

        branch = _git("branch", "--show-current")
        last_msg = _git("log", "-1", "--format=%s")[:80]
        last_time = _git("log", "-1", "--format=%ar")
        last_iso = _git("log", "-1", "--format=%aI")
        tag = _git("describe", "--tags", "--abbrev=0") or ""
        dirty_raw = _git("status", "--porcelain")
        dirty = len([line for line in dirty_raw.split("\n") if line.strip()])
        week_commits_raw = _git("log", "--oneline", "--since=7 days ago")
        week_commits = len([line for line in week_commits_raw.split("\n") if line.strip()])

        return {
            "repo_found": True, "repo_path": str(repo_dir), "branch": branch,
            "last_commit": last_msg, "last_commit_time": last_time,
            "last_commit_iso": last_iso, "tag": tag, "dirty_files": dirty,
            "week_commits": week_commits,
        }
    except Exception:
        return {"repo_found": True, "repo_path": str(repo_dir)}


def project_cn(pid: str) -> str:
    _names = {
        "lingflow": "灵通", "lingclaude": "灵克", "lingzhi": "灵知",
        "lingyi": "灵依", "lingtongask": "灵通问道", "lingterm": "灵犀",
        "lingminopt": "灵极优", "lingresearch": "灵研", "zhibridge": "智桥",
        "lingyang": "灵扬", "guangda": "广大老师",
    }
    return _names.get(pid, pid)
