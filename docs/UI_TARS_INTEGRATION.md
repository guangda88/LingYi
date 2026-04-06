# UI-TARS集成使用指南

UI-TARS是字节开源的多模态AI Agent栈，提供"视觉-操作"闭环能力。LingYi已集成UI-TARS，可通过工具调用实现网页截图、OCR识别、UI元素查找等功能。

## 功能概述

| 工具名称 | 功能 | 应用场景 |
|---------|------|---------|
| `ui_capture` | 捕获网页截图 | 竞品监控、舆情分析、界面审计 |
| `ui_ocr` | 识别图像文字 | 诊断书识别、古籍数字化、图片内容提取 |
| `ui_find` | 查找UI元素 | 自动化测试、界面导航、元素定位 |
| `ui_analyze` | 分析UI界面状态 | 页面结构分析、交互元素识别 |
| `ui_status` | 获取UI-TARS服务状态 | 服务健康检查 |

## 快速开始

### 1. 安装依赖

```bash
pip install pillow requests
```

### 2. 启动UI-TARS服务

#### 方式A：使用真实UI-TARS（推荐）

```bash
# 克隆UI-TARS仓库
git clone https://github.com/bytedance/UI-TARS-desktop.git
cd UI-TARS-desktop

# 安装依赖
npm install
npm install puppeteer

# 启动API服务
npm start -- --api-port 5000
```

#### 方式B：使用模拟服务（测试用）

```bash
cd /home/ai/LingYi
python3 scripts/ui_tars_mock.py --port 5000
```

### 3. 启用LingYi UI功能

```bash
# 设置环境变量
export UI_TARS_ENABLED=true
export UI_TARS_API_URL=http://localhost:5000

# 重启LingYi Web服务
pkill -f "lingyi.*web"
python3 -m lingyi.cli web --port 8900
```

### 4. 测试功能

```bash
cd /home/ai/LingYi
export UI_TARS_ENABLED=true
python3 scripts/test_ui_tars.py
```

## 使用示例

### 示例1：灵通问道 - 竞品监控

```python
# 在灵通问道中监控竞品微博

from lingyi.tools import execute_tool

# 1. 截取竞品微博页面
result = execute_tool("ui_capture", {
    "url": "https://weibo.com/competitor",
    "width": 1920,
    "height": 1080
})

# 2. OCR识别最新微博内容
image_path = result.split(": ")[1].split(" (")[0]
ocr_result = execute_tool("ui_ocr", {
    "image_path": image_path
})

# 3. 分析互动元素（点赞、评论、转发）
elements = execute_tool("ui_find", {
    "image_path": image_path,
    "element_type": "button",
    "text": "评论"
})

# 4. 记录到备忘
execute_tool("memo_add", {
    "content": f"竞品最新微博: {ocr_result}\n互动元素: {elements}"
})
```

### 示例2：灵知 - 诊断书识别

```python
# 在灵知中识别中医诊断书

from lingyi.tools import execute_tool

# 1. 截取或上传诊断书图片
# （假设图片已保存到 /tmp/diagnosis.png）

# 2. OCR识别诊断书内容
ocr_result = execute_tool("ui_ocr", {
    "image_path": "/tmp/diagnosis.png"
})

# 3. 提取关键信息（日期、诊断、处方）
from lingyi.ask import ask

diagnosis = ask(
    f"从以下OCR结果中提取诊断日期、主要诊断和处方：\n{ocr_result}"
)

# 4. 添加到日程（提醒复诊）
execute_tool("memo_add", {
    "content": f"诊断记录: {diagnosis}"
})
```

### 示例3：自动化竞品监控流程

```python
# 完整的竞品监控自动化流程

import time
from lingyi.tools import execute_tool

def monitor_competitors():
    """监控多个竞品的社交媒体"""

    competitors = [
        {"name": "竞品A", "url": "https://weibo.com/comp_a"},
        {"name": "竞品B", "url": "https://weibo.com/comp_b"},
    ]

    for comp in competitors:
        # 1. 截图
        result = execute_tool("ui_capture", {
            "url": comp["url"],
            "width": 1920,
            "height": 1080
        })

        if "截图成功" not in result:
            continue

        image_path = result.split(": ")[1].split(" (")[0]

        # 2. OCR识别
        ocr_result = execute_tool("ui_ocr", {
            "image_path": image_path
        })

        # 3. 分析UI状态
        analysis = execute_tool("ui_analyze", {
            "image_path": image_path
        })

        # 4. 记录结果
        execute_tool("memo_add", {
            "content": f"""【竞品监控】{comp['name']}
时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
URL: {comp['url']}
OCR识别: {ocr_result[:500]}
UI分析: {analysis[:500]}
"""
        })

        # 避免频繁请求
        time.sleep(5)

    return "监控完成"

# 执行监控
result = monitor_competitors()
print(result)
```

## Web界面使用

在LingYi WebUI（https://100.66.1.8:8900/）中，可以直接通过对话调用UI功能：

```
你：帮我截一下竞品的微博页面，看看他们发了什么

灵依：[自动调用 ui_capture → ui_ocr]

已获取竞品微博截图：
截图路径: /home/ai/.lingyi/ui_screenshots/screenshot_20260407.png

OCR识别内容：
[识别的文字内容...]

[自动分析并总结]
```

## 架构设计

```
┌─────────────┐                    ┌─────────────┐
│  LingYi     │  HTTP API (JSON)  │  UI-TARS     │
│  (灵依)     │ ─────────────────→│  (Docker)   │
│             │←───────────────── │              │
└─────────────┘                    └─────────────┘
     ↓                                    ↓
工具注册                              截图/OCR/操作
     ↓                                    ↓
返回结果                              JSON响应
     ↓
灵通问道 / 灵知应用
```

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|-------|--------|------|
| `UI_TARS_ENABLED` | false | 是否启用UI功能 |
| `UI_TARS_API_URL` | http://localhost:5000 | UI-TARS服务地址 |

### 服务端点

UI-TARS需要提供以下HTTP API端点：

```
GET  /health          - 健康检查
POST /screenshot      - 网页截图
POST /ocr            - OCR识别
POST /find_elements  - 查找UI元素
POST /analyze        - UI分析
```

## 常见问题

### Q: UI-TARS服务不可用怎么办？

A: 检查以下几点：
1. 确认UI-TARS服务已启动：`ps aux | grep ui_tars`
2. 检查环境变量：`echo $UI_TARS_ENABLED`
3. 测试服务连接：`curl http://localhost:5000/health`
4. 查看服务日志：`tail -f /tmp/ui_tars_mock.log`

### Q: 截图保存到哪里？

A: 截图默认保存在 `~/.lingyi/ui_screenshots/` 目录，文件名格式为 `screenshot_YYYYMMDD_HHMMSS.png`

### Q: OCR识别准确率如何？

A: 准确率取决于：
1. 图像质量（分辨率、清晰度）
2. 文字字体和排版
3. 是否有干扰元素（水印、背景复杂）
4. 使用真实UI-TARS时准确率会更高

### Q: 可以识别手写文字吗？

A: 可以，但准确率相对较低。建议：
1. 确保图片清晰、光照良好
2. 尽量使用标准字体
3. 对重要内容进行人工复核

## 扩展开发

### 添加新的UI工具

在 `src/lingyi/tools.py` 中添加：

```python
def _ui_custom_action(image_path: str) -> str:
    """自定义UI操作"""
    try:
        from .ui_tars import custom_function
        result = custom_function(image_path)
        return f"操作成功: {result}"
    except Exception as e:
        return f"操作失败: {e}"

_register("ui_custom", "自定义UI操作", {
    "image_path": {"type": "string", "description": "图像文件路径"},
}, ["image_path"], _ui_custom_action)
```

### 集成到灵通问道

在灵通问道中添加自动化监控任务：

```python
# /home/ai/lingtongask/monitoring.py

import schedule
from lingyi.tools import execute_tool

def daily_competitor_monitor():
    """每日竞品监控任务"""
    execute_tool("ui_capture", {"url": "https://weibo.com/competitor"})
    # ... 后续处理

# 每天早上6点执行
schedule.every().day.at("06:00").do(daily_competitor_monitor)
```

## 性能优化

1. **截图缓存**：对相同URL的截图进行缓存，避免重复请求
2. **异步处理**：使用后台任务处理耗时操作
3. **限流控制**：避免过于频繁的请求被服务拒绝
4. **批量处理**：一次性处理多个URL，减少网络开销

## 安全考虑

1. **权限控制**：UI-TARS服务应仅对本地访问开放
2. **内容过滤**：避免捕获敏感信息
3. **存储清理**：定期清理截图文件，避免磁盘占满
4. **访问日志**：记录所有UI操作，便于审计

## 后续规划

- [ ] 集成真实UI-TARS（非模拟服务）
- [ ] 支持视频截图和分析
- [ ] 添加UI操作功能（点击、输入等）
- [ ] 优化OCR识别准确率
- [ ] 添加模板匹配能力

## 参考资料

- [UI-TARS GitHub](https://github.com/bytedance/UI-TARS-desktop)
- [LingYi WebUI](https://100.66.1.8:8900/)
- [灵通问道文档](https://github.com/guangda88/lingtongask)
