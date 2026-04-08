"""端点健康监控 - 检测灵字辈成员在线状态。

功能：
- 定期ping所有端点
- 维护在线状态映射
- 提供健康状态查询API
- 在Web UI中展示状态
"""

import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

_HEALTH_STATE_PATH = Path.home() / ".lingyi" / "endpoint_health.json"

# 端点配置
_ENDPOINTS = {
    "lingyi": {"name": "灵依", "port": 8900, "url": "https://127.0.0.1:8900/api/status"},
    "lingzhi": {"name": "灵知", "port": 8000, "url": "http://127.0.0.1:8000/api/v1/health"},
    "lingzhi_auto": {"name": "灵知(auto)", "port": 8011, "url": "http://127.0.0.1:8011/api/v1/health"},
    "lingminopt": {"name": "灵极优", "port": 8002, "url": "http://127.0.0.1:8002/api/health"},
    "lingresearch": {"name": "灵妍", "port": 8003, "url": "http://127.0.0.1:8003/api/health"},
    "lingclaude": {"name": "灵克", "port": 8700, "url": "http://127.0.0.1:8700/api/health"},
    "lingflow": {"name": "灵通", "port": 8600, "url": "http://127.0.0.1:8600/api/status"},
    "zhibridge": {"name": "智桥", "port": 8765, "url": "http://127.0.0.1:8765/health"},
    "lingyang": {"name": "灵扬", "port": 8021, "url": "http://127.0.0.1:8021/api/health"},
}

_PING_TIMEOUT = 3  # 秒
_SAVE_INTERVAL = 60  # 秒


@dataclass
class EndpointStatus:
    """端点状态"""
    member_id: str
    name: str
    online: bool
    last_check: str
    last_online: str | None = None
    response_time_ms: float = 0
    error: str | None = None


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def load_health_state() -> Dict[str, dict]:
    """加载健康状态文件"""
    if not _HEALTH_STATE_PATH.exists():
        return {}
    try:
        data = json.loads(_HEALTH_STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception as e:
        logger.warning(f"Failed to load health state: {e}")
    return {}


def save_health_state(state: Dict[str, dict]) -> None:
    """保存健康状态文件"""
    try:
        _HEALTH_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _HEALTH_STATE_PATH.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"Failed to save health state: {e}")


def ping_endpoint(member_id: str) -> EndpointStatus:
    """Ping单个端点，返回状态"""
    if member_id not in _ENDPOINTS:
        return EndpointStatus(
            member_id=member_id,
            name="未知",
            online=False,
            last_check=_now(),
            error=f"Unknown endpoint: {member_id}"
        )

    config = _ENDPOINTS[member_id]
    url = config["url"]

    try:
        import urllib.request
        import urllib.error
        import time as _time

        start = _time.time()
        req = urllib.request.Request(url, method="GET")
        ctx = None
        if url.startswith("https"):
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = 0

        with urllib.request.urlopen(req, context=ctx, timeout=_PING_TIMEOUT) as resp:
            response_time_ms = (_time.time() - start) * 1000
            if resp.status == 200:
                return EndpointStatus(
                    member_id=member_id,
                    name=config["name"],
                    online=True,
                    last_check=_now(),
                    last_online=_now(),
                    response_time_ms=round(response_time_ms, 2),
                )
            else:
                return EndpointStatus(
                    member_id=member_id,
                    name=config["name"],
                    online=False,
                    last_check=_now(),
                    error=f"HTTP {resp.status}"
                )
    except urllib.error.HTTPError as e:
        return EndpointStatus(
            member_id=member_id,
            name=config["name"],
            online=False,
            last_check=_now(),
            error=f"HTTP {e.code}"
        )
    except Exception as e:
        return EndpointStatus(
            member_id=member_id,
            name=config["name"],
            online=False,
            last_check=_now(),
            error=str(e)[:100]  # 限制错误信息长度
        )


def check_all_endpoints() -> Dict[str, EndpointStatus]:
    """检查所有端点健康状态"""
    results = {}
    existing_state = load_health_state()

    for member_id, config in _ENDPOINTS.items():
        # Ping当前状态
        status = ping_endpoint(member_id)

        # 如果离线但之前在线，保留last_online时间
        if not status.online and member_id in existing_state:
            last_online = existing_state[member_id].get("last_online")
            if last_online:
                status.last_online = last_online

        results[member_id] = status

    # 保存状态
    save_health_state({
        mid: asdict(status) for mid, status in results.items()
    })

    return results


def get_health_summary() -> dict:
    """获取健康状态摘要"""
    state = load_health_state()
    online_count = sum(1 for s in state.values() if s.get("online", False))
    total_count = len(state)

    return {
        "total": total_count,
        "online": online_count,
        "offline": total_count - online_count,
        "online_rate": round(online_count / total_count * 100, 1) if total_count > 0 else 0,
        "endpoints": state,
        "last_check": max(
            (s.get("last_check", "") for s in state.values()),
            default=""
        )
    }


def format_health_summary(summary: dict) -> str:
    """格式化健康状态摘要"""
    lines = [
        "🏥 灵字辈端点健康状态",
        f"在线: {summary['online']}/{summary['total']} ({summary['online_rate']}%)",
        f"上次检查: {summary['last_check'][:16] if summary['last_check'] else '无'}",
        "=" * 50,
    ]

    for mid, status in summary["endpoints"].items():
        icon = "🟢" if status.get("online", False) else "🔴"
        name = status.get("name", mid)
        response_time = status.get("response_time_ms", 0)
        error = status.get("error", "")

        line = f"{icon} {name} ({mid})"
        if status.get("online", False):
            line += f" - {response_time:.0f}ms"
        else:
            last_online = status.get("last_online", "")
            if last_online:
                last_online_str = last_online[:16].replace("T", " ")
                line += f" - 离线 (上次在线: {last_online_str})"
            else:
                line += " - 离线"

        lines.append(line)
        if error:
            lines.append(f"   错误: {error}")

    return "\n".join(lines)


class HealthMonitor:
    """健康监控器（后台任务）"""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.running = False

    def start(self):
        """启动监控（阻塞）"""
        logger.info(f"启动端点健康监控，间隔: {self.check_interval}秒")
        self.running = True

        while self.running:
            try:
                results = check_all_endpoints()
                online_count = sum(1 for s in results.values() if s.online)
                total_count = len(results)
                logger.info(
                    f"健康检查完成: {online_count}/{total_count} 在线"
                )
            except Exception as e:
                logger.error(f"健康检查失败: {e}")

            time.sleep(self.check_interval)

    def stop(self):
        """停止监控"""
        self.running = False


if __name__ == "__main__":
    # 测试模式
    print(format_health_summary(get_health_summary()))
