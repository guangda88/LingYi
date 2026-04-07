"""灵依巡检：检查所有项目的重要变化，生成报告。"""

import os
import subprocess
from datetime import datetime, timedelta

from .config import load_patrol_paths

SINCE_HOURS = 3


def run_git(path: str, *args: str) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", path] + list(args),
            capture_output=True, text=True, timeout=10,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def check_project(name: str, path: str) -> dict:
    info = {"name": name, "path": path, "changes": []}

    if not os.path.isdir(os.path.join(path, ".git")):
        info["status"] = "无git仓库"
        return info

    since = (datetime.now() - timedelta(hours=SINCE_HOURS)).strftime("%Y-%m-%d %H:%M")
    log = run_git(path, "log", "--oneline", f"--since={since}")
    if log:
        info["changes"].append(f"最近{SINCE_HOURS}h提交:\n  " + log.replace("\n", "\n  "))

    diff = run_git(path, "diff", "--stat")
    if diff:
        info["changes"].append("未暂存修改:\n  " + diff.replace("\n", "\n  "))

    staged = run_git(path, "diff", "--cached", "--stat")
    if staged:
        info["changes"].append("已暂存未提交:\n  " + staged.replace("\n", "\n  "))

    status_short = run_git(path, "status", "--short")
    untracked = [l for l in status_short.split("\n") if l.startswith("??")]
    if untracked:
        info["changes"].append(f"未跟踪文件({len(untracked)}个)")

    branch = run_git(path, "branch", "--show-current") or "master"
    info["branch"] = branch

    last_commit = run_git(path, "log", "-1", "--format=%h %ai %s")
    info["last_commit"] = last_commit

    info["status"] = "有变化" if info["changes"] else "无变化"
    return info


def generate_report() -> str:
    projects = load_patrol_paths()
    if not projects:
        return "未配置巡检项目路径（检查 ~/.lingyi/presets.json 的 patrol_paths）。"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"📋 灵依巡检报告 — {now}", "=" * 50, ""]

    changed = []
    silent = []

    for name, path in projects.items():
        info = check_project(name, path)
        if info["status"] == "有变化":
            changed.append(info)
        else:
            silent.append(info)

    if changed:
        lines.append(f"🔔 有变化的项目（{len(changed)}个）：")
        lines.append("")
        for info in changed:
            lines.append(f"【{info['name']}】分支 {info.get('branch', '?')}")
            for c in info["changes"]:
                lines.append(f"  {c}")
            lines.append(f"  最近提交: {info.get('last_commit', '无')}")
            lines.append("")

    lines.append(f"✅ 无变化的项目（{len(silent)}个）：")
    for info in silent:
        last = info.get('last_commit', '')
        lines.append(f"  {info['name']} — {info['status']}" + (f" | {last}" if last else ""))

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_report())
