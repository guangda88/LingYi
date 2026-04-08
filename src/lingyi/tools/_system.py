"""系统工具 — Shell/文件/Git/代码统计/UI-TARS。"""

from __future__ import annotations

from ._registry import _register


# ── Shell 执行 ────────────────────────────────────────

def _shell_exec(command: str, timeout: int = 15) -> str:
    # [安全禁用] 此功能因命令注入风险已被禁用
    return "[安全策略] shell_exec 功能已禁用（命令注入风险）。如需执行命令，请使用特定的工具函数。"

# _register("shell_exec", ... 已禁用


# ── 文件读取 ──────────────────────────────────────────

def _file_read(path: str, lines: int = 100, offset: int = 0) -> str:
    from pathlib import Path as _P
    try:
        p = _P(path).expanduser().resolve()
        _ALLOWED_DIRS = ["/home/ai/LingYi", "/home/ai/LingFlow", "/home/ai/LingClaude", "/tmp"]
        real = str(p)
        if not any(real.startswith(d) for d in _ALLOWED_DIRS):
            return f"安全策略: 不允许读取此路径 ({path})"
        if not p.exists():
            return f"文件不存在: {path}"
        if not p.is_file():
            return f"不是文件: {path}"
        if p.stat().st_size > 2_000_000:
            return f"文件太大（{p.stat().st_size // 1024}KB），请用 shell_exec + head/tail 查看"
        text = p.read_text(encoding="utf-8", errors="replace")
        all_lines = text.splitlines()
        total = len(all_lines)
        start = max(0, offset)
        end = min(total, start + lines)
        selected = all_lines[start:end]
        header = f"文件: {p} (共{total}行, 显示 {start+1}-{end})\n"
        numbered = "\n".join(f"{start+i+1:6d}| {line}" for i, line in enumerate(selected))
        return header + numbered
    except Exception as e:
        return f"读取失败: {e}"


_register("file_read", "读取文件内容（带行号）", {
    "path": {"type": "string", "description": "文件路径"},
    "lines": {"type": "integer", "description": "读取行数（默认100）"},
    "offset": {"type": "integer", "description": "起始行号偏移（默认0）"},
}, ["path"], _file_read)


# ── Git 状态 ──────────────────────────────────────────

def _git_status(project: str = "") -> str:
    import os
    import subprocess
    projects = {
        "灵通": "/home/ai/LingFlow",
        "灵知": "/home/ai/zhineng-knowledge-system",
        "灵依": "/home/ai/LingYi",
        "灵克": "/home/ai/LingClaude",
        "灵极优": "/home/ai/LingMinOpt",
        "灵研": "/home/ai/lingresearch",
        "灵信": "/home/ai/LingMessage",
    }
    if project:
        matched = {k: v for k, v in projects.items() if project.lower() in k.lower() or project.lower() in v.lower()}
        if not matched:
            return "未找到项目: " + project
    else:
        matched = projects

    results: list[str] = []
    for name, path in matched.items():
        if not os.path.isdir(path):
            results.append(f"{name}: 目录不存在")
            continue
        try:
            branch = subprocess.run(["git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD"],
                                    capture_output=True, text=True, timeout=5).stdout.strip()
            short = subprocess.run(["git", "-C", path, "log", "-1", "--format=%h %s (%cr)"],
                                   capture_output=True, text=True, timeout=5).stdout.strip()
            dirty = subprocess.run(["git", "-C", path, "status", "--porcelain"],
                                   capture_output=True, text=True, timeout=5).stdout.strip()
            dirty_count = len([ln for ln in dirty.splitlines() if ln.strip()]) if dirty else 0
            status = f"修改{dirty_count}个文件" if dirty_count else "干净"
            results.append(f"{name} [{branch}] {status}\n  最近: {short}")
        except Exception as e:
            results.append(f"{name}: 查询失败 ({e})")
    return "\n\n".join(results)


_register("git_status", "查看灵字辈项目的 Git 状态", {
    "project": {"type": "string", "description": "项目名称（可选，留空查看全部）"},
}, executor=_git_status)


# ── 代码统计 ──────────────────────────────────────────

def _code_stats(project: str = "") -> str:
    import subprocess
    import os

    projects = {
        "灵通": "/home/ai/LingFlow",
        "灵知": "/home/ai/zhineng-knowledge-system",
        "灵依": "/home/ai/LingYi",
        "灵克": "/home/ai/LingClaude",
        "灵极优": "/home/ai/LingMinOpt",
        "灵研": "/home/ai/lingresearch",
        "灵通问道": "/home/ai/lingtongask",
        "灵犀": "/home/ai/Ling-term-mcp",
        "灵信": "/home/ai/LingMessage",
        "灵扬": "/home/ai/LingYang",
        "灵通官网": "/home/ai/lingflow.top",
    }

    if project:
        pl = project.lower()
        matched = {k: v for k, v in projects.items() if pl in k.lower() or pl in v.lower()}
        if not matched:
            return "未找到项目: " + project + "。可用: " + ", ".join(projects.keys())
    else:
        matched = projects

    results: list[tuple[str, int]] = []
    total = 0
    for name, path in matched.items():
        if not os.path.isdir(path):
            continue
        try:
            r = subprocess.run(
                ["find", path, "-name", "*.py",
                 "-not", "-path", "*/__pycache__/*",
                 "-not", "-path", "*/.git/*",
                 "-not", "-path", "*/venv/*",
                 "-not", "-path", "*/.venv/*",
                 "-not", "-path", "*/site-packages/*",
                 "-not", "-path", "*/node_modules/*",
                 "-exec", "wc", "-l", "{}", "+"],
                capture_output=True, text=True, timeout=15
            )
            count = 0
            for line in r.stdout.strip().split("\n"):
                parts = line.strip().split()
                if parts and parts[0].isdigit():
                    count += int(parts[0])
            total += count
            results.append((name, count))
        except Exception:
            results.append((name, 0))

    if not project:
        out = ["灵字辈代码量统计（Python）：", ""]
        for n, c in sorted(results, key=lambda x: -x[1]):
            out.append("  " + n + "：" + format(c, ",") + " 行")
        out.append("")
        out.append("  总计：" + format(total, ",") + " 行")
        return "\n".join(out)
    else:
        n, c = results[0] if results else ("?", 0)
        return n + " Python代码量：" + format(c, ",") + " 行"


_register("code_stats", "统计灵字辈项目的代码量", {
    "project": {"type": "string", "description": "项目名称（可选，留空统计全部）"},
}, executor=_code_stats)


# ── UI-TARS 视觉-操作闭环 ─────────────────────────────────

def _ui_capture_screenshot(url: str, width: int = 1920, height: int = 1080) -> str:
    """捕获网页截图"""
    try:
        from ..ui_tars import capture_screenshot
        result = capture_screenshot(url, width=width, height=height)
        return f"截图成功: {result['image_path']} ({result['width']}x{result['height']})"
    except Exception as e:
        return f"截图失败: {e}"


def _ui_ocr(image_path: str, x: int | None = None, y: int | None = None,
            width: int | None = None, height: int | None = None) -> str:
    """识别图像中的文字（OCR）"""
    try:
        from ..ui_tars import ocr_image
        region = None
        if x is not None and y is not None and width is not None and height is not None:
            region = {"x": x, "y": y, "width": width, "height": height}

        result = ocr_image(image_path, region=region)
        lines = [
            f"识别成功（置信度: {result['confidence']:.2f}）",
            f"文字内容:\n{result['text']}",
        ]
        if result.get('lines'):
            lines.append(f"\n逐行识别 ({len(result['lines'])} 行):")
            for i, line in enumerate(result['lines'][:10], 1):
                lines.append(f"  {i}. {line.get('text', '')}")

        return "\n".join(lines)
    except Exception as e:
        return f"OCR识别失败: {e}"


def _ui_find_elements(image_path: str, element_type: str = "button", text: str | None = None) -> str:
    """在图像中查找UI元素"""
    try:
        from ..ui_tars import find_elements
        result = find_elements(image_path, element_type=element_type, text=text)

        if result['count'] == 0:
            return f"未找到类型为 {element_type} 的元素"

        lines = [f"找到 {result['count']} 个 {element_type} 元素:"]
        for i, elem in enumerate(result['elements'][:10], 1):
            bbox = elem.get('bbox', {})
            lines.append(f"  {i}. 位置: ({bbox.get('x', 0)}, {bbox.get('y', 0)}) "
                        f"大小: {bbox.get('width', 0)}x{bbox.get('height', 0)}")
            if elem.get('text'):
                lines.append(f"      文字: {elem['text']}")
            if elem.get('confidence'):
                lines.append(f"      置信度: {elem['confidence']:.2f}")

        return "\n".join(lines)
    except Exception as e:
        return f"元素查找失败: {e}"


def _ui_analyze(image_path: str) -> str:
    """分析UI界面状态"""
    try:
        from ..ui_tars import analyze_ui_state
        result = analyze_ui_state(image_path)

        lines = [
            f"UI类型: {result['ui_type']}",
            f"摘要: {result['summary']}",
        ]
        if result.get('text_content'):
            lines.append(f"\n主要文字内容:\n{result['text_content'][:500]}")
        if result.get('interactive_elements'):
            lines.append(f"\n可交互元素 ({len(result['interactive_elements'])} 个):")
            for elem in result['interactive_elements'][:5]:
                lines.append(f"  - {elem.get('type', 'unknown')}: {elem.get('text', elem.get('selector', ''))}")

        return "\n".join(lines)
    except Exception as e:
        return f"UI分析失败: {e}"


def _ui_status() -> str:
    """获取UI-TARS服务状态"""
    try:
        from ..ui_tars import get_status
        status = get_status()

        lines = ["UI-TARS服务状态:"]
        lines.append(f"  启用: {'是' if status['enabled'] else '否'}")
        lines.append(f"  可用: {'是' if status['available'] else '否'}")
        lines.append(f"  API地址: {status['api_url']}")
        if status.get('version'):
            lines.append(f"  版本: {status['version']}")

        if status['enabled'] and not status['available']:
            lines.append("\n⚠️ UI功能已启用但服务不可用，请检查UI-TARS服务状态")

        return "\n".join(lines)
    except Exception as e:
        return f"状态查询失败: {e}"


_register("ui_capture", "捕获网页截图", {
    "url": {"type": "string", "description": "目标网页URL"},
    "width": {"type": "integer", "description": "截图宽度（默认1920）"},
    "height": {"type": "integer", "description": "截图高度（默认1080）"},
}, ["url"], _ui_capture_screenshot)

_register("ui_ocr", "识别图像中的文字（OCR）", {
    "image_path": {"type": "string", "description": "图像文件路径"},
    "x": {"type": "integer", "description": "识别区域左上角X坐标（可选）"},
    "y": {"type": "integer", "description": "识别区域左上角Y坐标（可选）"},
    "width": {"type": "integer", "description": "识别区域宽度（可选）"},
    "height": {"type": "integer", "description": "识别区域高度（可选）"},
}, ["image_path"], _ui_ocr)

_register("ui_find", "在图像中查找UI元素", {
    "image_path": {"type": "string", "description": "图像文件路径"},
    "element_type": {"type": "string", "description": "元素类型（button/text/image/link）"},
    "text": {"type": "string", "description": "元素文本内容（可选）"},
}, ["image_path", "element_type"], _ui_find_elements)

_register("ui_analyze", "分析UI界面状态", {
    "image_path": {"type": "string", "description": "图像文件路径"},
}, ["image_path"], _ui_analyze)

_register("ui_status", "获取UI-TARS服务状态", {}, executor=_ui_status)
