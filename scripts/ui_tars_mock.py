#!/usr/bin/env python3
"""UI-TARS模拟服务 - 用于测试LingYi的UI功能集成

这是一个轻量级的UI-TARS API模拟器，提供以下端点：
- GET /health - 健康检查
- POST /screenshot - 网页截图（模拟）
- POST /ocr - OCR识别（模拟）
- POST /find_elements - UI元素查找（模拟）
- POST /analyze - UI分析（模拟）

使用方法:
    python scripts/ui_tars_mock.py              # 启动服务（端口5000）
    python scripts/ui_tars_mock.py --port 6000  # 指定端口
"""

import base64
import json
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse, parse_qs

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MockUIARSHandler(BaseHTTPRequestHandler):
    """UI-TARS模拟API处理器"""

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        """发送JSON响应"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_error(self, message: str, status: int = 400) -> None:
        """发送错误响应"""
        self._send_json({"success": False, "error": message}, status)

    def _read_json(self) -> dict[str, Any] | None:
        """读取JSON请求体"""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            return json.loads(body) if body else {}
        except Exception as e:
            logger.error(f"读取JSON失败: {e}")
            return None

    def do_GET(self) -> None:
        """处理GET请求"""
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/health":
            self._send_json({
                "success": True,
                "status": "ok",
                "version": "0.1.0-mock",
            })
        else:
            self._send_error(f"未知路径: {parsed_path.path}", 404)

    def do_POST(self) -> None:
        """处理POST请求"""
        parsed_path = urlparse(self.path)
        data = self._read_json()

        if not data:
            self._send_error("无效的JSON请求体")
            return

        if parsed_path.path == "/screenshot":
            self._handle_screenshot(data)
        elif parsed_path.path == "/ocr":
            self._handle_ocr(data)
        elif parsed_path.path == "/find_elements":
            self._handle_find_elements(data)
        elif parsed_path.path == "/analyze":
            self._handle_analyze(data)
        else:
            self._send_error(f"未知路径: {parsed_path.path}", 404)

    def _handle_screenshot(self, data: dict[str, Any]) -> None:
        """处理截图请求（模拟）"""
        url = data.get("url", "")
        width = data.get("width", 1920)
        height = data.get("height", 1080)

        logger.info(f"模拟截图: {url} ({width}x{height})")

        # 生成一个简单的占位图片（纯色PNG）
        # 真实的UI-TARS会使用Puppeteer/Selenium
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (width, height), color="#f0f0f0")
        draw = ImageDraw.Draw(img)

        # 添加一些模拟的UI元素
        draw.rectangle([50, 50, width - 50, 100], fill="#3498db")
        draw.text([width // 2 - 100, 60], "模拟浏览器窗口", fill="white")

        draw.rectangle([50, 120, width - 50, height - 50], fill="white")
        draw.text([100, 140], f"URL: {url[:50]}...", fill="#333")

        # 保存到内存
        import io
        img_buffer = io.BytesIO()
        img.save(img_buffer, format="PNG")
        img_buffer.seek(0)

        # Base64编码
        image_data = base64.b64encode(img_buffer.read()).decode("utf-8")

        self._send_json({
            "success": True,
            "image_data": image_data,
            "width": width,
            "height": height,
            "timestamp": time.time(),
        })

    def _handle_ocr(self, data: dict[str, Any]) -> None:
        """处理OCR请求（模拟）"""
        image_path = data.get("image_path", "")
        region = data.get("region")

        logger.info(f"模拟OCR: {image_path}")

        # 模拟识别结果
        text = "这是模拟的OCR识别结果。\n在实际的UI-TARS中，这里会返回真实的文字识别结果。"

        lines = [
            {"text": "这是模拟的OCR识别结果", "confidence": 0.95},
            {"text": "在实际的UI-TARS中", "confidence": 0.92},
            {"text": "这里会返回真实的文字识别结果", "confidence": 0.88},
        ]

        self._send_json({
            "success": True,
            "text": text,
            "confidence": 0.92,
            "lines": lines,
            "regions": [{"x": 0, "y": 0, "width": 500, "height": 100}],
        })

    def _handle_find_elements(self, data: dict[str, Any]) -> None:
        """处理元素查找请求（模拟）"""
        image_path = data.get("image_path", "")
        element_type = data.get("element_type", "button")
        text = data.get("text")

        logger.info(f"模拟元素查找: {image_path}, type={element_type}, text={text}")

        # 模拟找到的元素
        elements = [
            {
                "type": element_type,
                "text": "提交",
                "bbox": {"x": 100, "y": 200, "width": 100, "height": 40},
                "confidence": 0.95,
                "selector": f"#{element_type}-submit",
            },
            {
                "type": element_type,
                "text": "取消",
                "bbox": {"x": 220, "y": 200, "width": 100, "height": 40},
                "confidence": 0.90,
                "selector": f"#{element_type}-cancel",
            },
        ]

        # 如果指定了文本，只返回匹配的元素
        if text:
            elements = [e for e in elements if text in e.get("text", "")]

        self._send_json({
            "success": True,
            "elements": elements,
            "count": len(elements),
        })

    def _handle_analyze(self, data: dict[str, Any]) -> None:
        """处理UI分析请求（模拟）"""
        image_path = data.get("image_path", "")

        logger.info(f"模拟UI分析: {image_path}")

        # 模拟分析结果
        self._send_json({
            "success": True,
            "ui_type": "web",
            "layout": {
                "type": "flex",
                "direction": "column",
                "areas": ["header", "content", "footer"],
            },
            "interactive_elements": [
                {"type": "button", "text": "提交", "selector": "#submit-btn"},
                {"type": "input", "text": "用户名", "selector": "input[type='text']"},
                {"type": "link", "text": "查看详情", "selector": "a.details"},
            ],
            "text_content": "这是模拟的UI分析结果。包含页面标题、表单和链接等元素。",
            "summary": "Web页面，包含表单输入和提交按钮",
        })

    def log_message(self, format: str, *args) -> None:
        """禁用默认日志"""
        pass


def main():
    import argparse

    parser = argparse.ArgumentParser(description="UI-TARS模拟服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=5000, help="监听端口")

    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), MockUIARSHandler)

    logger.info(f"UI-TARS模拟服务启动: http://{args.host}:{args.port}")
    logger.info(f"健康检查: http://{args.host}:{args.port}/health")
    logger.info("按 Ctrl+C 停止服务")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("服务停止")
        server.shutdown()


if __name__ == "__main__":
    main()
