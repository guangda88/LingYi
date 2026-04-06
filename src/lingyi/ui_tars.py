"""UI-TARS客户端封装 - 视觉-操作闭环保驾护航

UI-TARS是字节开源的多模态AI Agent栈，提供屏幕截图、OCR识别、
元素定位等能力。本模块将其封装为LingYi可调用的工具。

架构：
┌─────────────┐  HTTP API  ┌─────────────┐
│  LingYi     │ ──────────→│  UI-TARS     │
│  (灵依)     │            │  (Docker)    │
└─────────────┘            └─────────────┘
     ↓                            ↓
工具调用                    截图/OCR/操作
     ↓                            ↓
返回结果                    JSON响应

环境变量：
- UI_TARS_API_URL: UI-TARS服务地址 (默认 http://localhost:5000)
- UI_TARS_ENABLED: 是否启用UI功能 (默认 false)
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# UI-TARS服务配置
_UI_TARS_API_URL = os.environ.get("UI_TARS_API_URL", "http://localhost:5000")
_UI_TARS_ENABLED = os.environ.get("UI_TARS_ENABLED", "false").lower() == "true"


class UIARSError(Exception):
    """UI-TARS调用错误"""
    pass


def _check_enabled() -> None:
    """检查UI-TARS是否启用"""
    if not _UI_TARS_ENABLED:
        raise UIARSError("UI-TARS功能未启用，请设置环境变量 UI_TARS_ENABLED=true")


def _check_service() -> bool:
    """检查UI-TARS服务是否可用"""
    try:
        r = requests.get(f"{_UI_TARS_API_URL}/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def capture_screenshot(url: str, width: int = 1920, height: int = 1080) -> dict[str, Any]:
    """捕获网页截图

    Args:
        url: 目标URL
        width: 截图宽度（默认1920）
        height: 截图高度（默认1080）

    Returns:
        包含截图信息的字典：
        {
            "success": bool,
            "image_path": str,  # 截图保存路径
            "width": int,
            "height": int,
            "timestamp": str
        }
    """
    _check_enabled()

    if not _check_service():
        raise UIARSError(f"UI-TARS服务不可用，请检查服务状态: {_UI_TARS_API_URL}")

    try:
        payload = {
            "url": url,
            "width": width,
            "height": height,
            "full_page": False,
        }
        r = requests.post(f"{_UI_TARS_API_URL}/screenshot", json=payload, timeout=30)
        r.raise_for_status()

        data = r.json()

        # 保存截图到临时文件
        if data.get("success") and "image_data" in data:
            import base64
            import time

            image_data = base64.b64decode(data["image_data"])
            temp_dir = Path.home() / ".lingyi" / "ui_screenshots"
            temp_dir.mkdir(parents=True, exist_ok=True)

            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            image_path = temp_dir / filename

            with open(image_path, "wb") as f:
                f.write(image_data)

            return {
                "success": True,
                "image_path": str(image_path),
                "width": width,
                "height": height,
                "timestamp": timestamp,
            }
        else:
            raise UIARSError(f"截图失败: {data.get('error', '未知错误')}")

    except requests.RequestException as e:
        raise UIARSError(f"UI-TARS服务调用失败: {e}")


def ocr_image(image_path: str, region: dict[str, int] | None = None) -> dict[str, Any]:
    """识别图像中的文字（OCR）

    Args:
        image_path: 图像文件路径
        region: 识别区域 {"x": 0, "y": 0, "width": 100, "height": 100}，None表示全图

    Returns:
        {
            "success": bool,
            "text": str,  # 识别的文字
            "confidence": float,  # 置信度
            "lines": list[dict],  # 逐行识别结果
            "regions": list[dict]  # 识别区域列表
        }
    """
    _check_enabled()

    if not Path(image_path).exists():
        raise UIARSError(f"图像文件不存在: {image_path}")

    try:
        payload = {"image_path": image_path}
        if region:
            payload["region"] = region

        r = requests.post(f"{_UI_TARS_API_URL}/ocr", json=payload, timeout=30)
        r.raise_for_status()

        data = r.json()

        if data.get("success"):
            return {
                "success": True,
                "text": data.get("text", ""),
                "confidence": data.get("confidence", 0.0),
                "lines": data.get("lines", []),
                "regions": data.get("regions", []),
            }
        else:
            raise UIARSError(f"OCR识别失败: {data.get('error', '未知错误')}")

    except requests.RequestException as e:
        raise UIARSError(f"UI-TARS服务调用失败: {e}")


def find_elements(
    image_path: str,
    element_type: str = "button",
    text: str | None = None,
) -> dict[str, Any]:
    """在图像中查找UI元素

    Args:
        image_path: 图像文件路径
        element_type: 元素类型（button/text/image/link等）
        text: 元素文本内容（可选）

    Returns:
        {
            "success": bool,
            "elements": list[dict],  # 找到的元素列表
            "count": int
        }
    """
    _check_enabled()

    if not Path(image_path).exists():
        raise UIARSError(f"图像文件不存在: {image_path}")

    try:
        payload = {
            "image_path": image_path,
            "element_type": element_type,
        }
        if text:
            payload["text"] = text

        r = requests.post(f"{_UI_TARS_API_URL}/find_elements", json=payload, timeout=30)
        r.raise_for_status()

        data = r.json()

        if data.get("success"):
            elements = data.get("elements", [])
            return {
                "success": True,
                "elements": elements,
                "count": len(elements),
            }
        else:
            raise UIARSError(f"元素查找失败: {data.get('error', '未知错误')}")

    except requests.RequestException as e:
        raise UIARSError(f"UI-TARS服务调用失败: {e}")


def analyze_ui_state(image_path: str) -> dict[str, Any]:
    """分析UI界面状态

    Args:
        image_path: 图像文件路径

    Returns:
        {
            "success": bool,
            "ui_type": str,  # 界面类型（web/app/desktop等）
            "layout": dict,  # 布局信息
            "interactive_elements": list[dict],  # 可交互元素
            "text_content": str,  # 主要文本内容
            "summary": str  # 界面摘要
        }
    """
    _check_enabled()

    if not Path(image_path).exists():
        raise UIARSError(f"图像文件不存在: {image_path}")

    try:
        payload = {"image_path": image_path}
        r = requests.post(f"{_UI_TARS_API_URL}/analyze", json=payload, timeout=30)
        r.raise_for_status()

        data = r.json()

        if data.get("success"):
            return {
                "success": True,
                "ui_type": data.get("ui_type", "unknown"),
                "layout": data.get("layout", {}),
                "interactive_elements": data.get("interactive_elements", []),
                "text_content": data.get("text_content", ""),
                "summary": data.get("summary", ""),
            }
        else:
            raise UIARSError(f"UI分析失败: {data.get('error', '未知错误')}")

    except requests.RequestException as e:
        raise UIARSError(f"UI-TARS服务调用失败: {e}")


def get_status() -> dict[str, Any]:
    """获取UI-TARS服务状态

    Returns:
        {
            "enabled": bool,
            "available": bool,
            "api_url": str,
            "version": str | None
        }
    """
    if not _UI_TARS_ENABLED:
        return {
            "enabled": False,
            "available": False,
            "api_url": _UI_TARS_API_URL,
            "version": None,
        }

    try:
        r = requests.get(f"{_UI_TARS_API_URL}/health", timeout=3)
        if r.status_code == 200:
            data = r.json()
            return {
                "enabled": True,
                "available": True,
                "api_url": _UI_TARS_API_URL,
                "version": data.get("version"),
            }
    except Exception:
        pass

    return {
        "enabled": True,
        "available": False,
        "api_url": _UI_TARS_API_URL,
        "version": None,
    }
