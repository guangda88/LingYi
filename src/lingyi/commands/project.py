"""项目 CLI 命令。"""

import click

from .. import project as proj_mod


def register(group: click.Group):
    @group.command("init")
    def project_init():
        """导入项目"""
        items = proj_mod.init_projects()
        if not items:
            click.echo("没有可导入的项目（检查 ~/.lingyi/presets.json）")
        else:
            click.echo(f"✓ 已导入 {len(items)} 个项目")

    @group.command("list")
    @click.option("--status", default=None, help="按状态筛选：active/maintenance/paused/archived")
    @click.option("--category", default=None, help="按分类筛选：core/knowledge/tool/…")
    def project_list(status: str | None, category: str | None):
        """项目看板"""
        if status or category:
            items = proj_mod.list_projects(status=status, category=category)
            if not items:
                click.echo("没有匹配的项目。")
                return
            for p in items:
                click.echo(proj_mod.format_project_short(p))
            return
        click.echo(proj_mod.format_project_kanban())

    @group.command("show")
    @click.argument("name")
    def project_show(name: str):
        """查看项目详情"""
        p = proj_mod.show_project(name)
        if not p:
            click.echo(f"项目「{name}」不存在。")
            return
        click.echo(proj_mod.format_project_detail(p))

    @group.command("add")
    @click.argument("name")
    @click.option("--alias", default="", help="别名")
    @click.option("--status", default="active", help="状态")
    @click.option("--priority", default="P3", help="优先级：P0/P1/P2/P3")
    @click.option("--category", default="tool", help="分类")
    @click.option("--desc", default="", help="说明")
    @click.option("--repo", default="", help="仓库名")
    @click.option("--version", default="", help="版本")
    @click.option("--energy", default=0, type=int, help="精力分配百分比")
    @click.option("--notes", default="", help="备注")
    def project_add(name: str, alias: str, status: str, priority: str, category: str,
                    desc: str, repo: str, version: str, energy: int, notes: str):
        """添加项目"""
        p = proj_mod.add_project(name, alias=alias, status=status, priority=priority,
                                 category=category, description=desc, repo=repo,
                                 version=version, energy_pct=energy, notes=notes)
        click.echo(f"✓ 项目「{p.name}」已添加")

    @group.command("update")
    @click.argument("name")
    @click.option("--alias", default=None, help="别名")
    @click.option("--status", default=None, help="状态")
    @click.option("--priority", default=None, help="优先级")
    @click.option("--category", default=None, help="分类")
    @click.option("--desc", default=None, help="说明")
    @click.option("--repo", default=None, help="仓库名")
    @click.option("--version", default=None, help="版本")
    @click.option("--energy", default=None, type=int, help="精力分配百分比")
    @click.option("--notes", default=None, help="备注")
    def project_update(name: str, alias: str | None, status: str | None, priority: str | None,
                       category: str | None, desc: str | None, repo: str | None,
                       version: str | None, energy: int | None, notes: str | None):
        """更新项目"""
        kwargs = {}
        if alias is not None: kwargs["alias"] = alias
        if status is not None: kwargs["status"] = status
        if priority is not None: kwargs["priority"] = priority
        if category is not None: kwargs["category"] = category
        if desc is not None: kwargs["description"] = desc
        if repo is not None: kwargs["repo"] = repo
        if version is not None: kwargs["version"] = version
        if energy is not None: kwargs["energy_pct"] = energy
        if notes is not None: kwargs["notes"] = notes
        p = proj_mod.update_project(name, **kwargs)
        if not p:
            click.echo(f"项目「{name}」不存在。")
            return
        click.echo(f"✓ 已更新「{p.name}」")
