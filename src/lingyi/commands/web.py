"""Web UI CLI 命令。"""

import click


def register(group: click.Group):
    @group.command("web")
    @click.option("--host", default="0.0.0.0", help="监听地址")
    @click.option("--port", default=8900, help="监听端口")
    @click.option("--no-ssl", is_flag=True, help="禁用HTTPS，使用HTTP")
    @click.option("--legacy", is_flag=True, help="使用旧版聊天界面")
    def do_web(host: str, port: int, no_ssl: bool, legacy: bool):
        """启动 Web UI（浏览器语音聊天）"""
        if legacy:
            from ..web import run_server
        else:
            from ..web_app import run_server
        run_server(host=host, port=port, ssl=not no_ssl)
