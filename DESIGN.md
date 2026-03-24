# YAMLPy - YAML-Driven Web Automation Framework

> 基于 Playwright + YAML 的下一代网页自动化框架

---

## 1. 项目概述

### 1.1 项目简介

**YAMLPy**（全称：YAML Automation with Playwright for Python）是一个完全通过 YAML 配置文件驱动网页自动化的 Python 框架。用户无需编写 Python 代码，仅通过声明式 YAML 即可定义复杂的多步骤自动化任务，并支持循环、定时调度、流程控制、条件分支等高级特性。

### 1.2 核心特性

| 特性 | 说明 |
|------|------|
| 🎯 YAML 驱动 | 所有任务逻辑通过 YAML 声明，无需写 Python 代码 |
| 🧩 模块化任务 | 支持任务复用、引用、继承 |
| 🔁 循环控制 | 支持固定次数循环、遍历数据循环 |
| ⏰ 定时调度 | 支持 Cron 表达式和间隔触发 |
| 🌲 条件分支 | 支持 if/else 条件判断 |
| 🔗 流程编排 | 支持任务链、多步骤编排 |
| 📸 截图/录制 | 支持步骤截图、全页截图、录像 |
| 📊 数据提取 | 支持从页面提取结构化数据 |
| 📝 日志/报告 | 完整的执行日志和 HTML 报告 |

---

## 2. 系统架构

```
┌─────────────────────────────────────────────────────┐
│                    YAMLPy                           │
│              (CLI / SDK / Web UI)                    │
├─────────────┬─────────────┬─────────────────────────┤
│  Task       │ Scheduler   │  Reporter               │
│  Engine     │ (apscheduler)│  (HTML/JSON Report)     │
├─────────────┴─────────────┴─────────────────────────┤
│              Core Engine (Python)                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │  YAML    │ │  Flow    │ │ Browser  │            │
│  │  Parser  │ │  Runner   │ │ Pool     │            │
│  └──────────┘ └──────────┘ └──────────┘            │
├─────────────────────────────────────────────────────┤
│           Playwright (Chromium/WebKit/Firefox)       │
└─────────────────────────────────────────────────────┘
```

### 2.1 核心模块

| 模块 | 路径 | 职责 |
|------|------|------|
| CLI | `src/cli.py` | 命令行入口 |
| Config | `src/config.py` | 全局配置管理 |
| Parser | `src/parser.py` | YAML 文件解析与校验 |
| FlowRunner | `src/flow_runner.py` | 流程执行引擎（循环/条件/任务链） |
| TaskExecutor | `src/task_executor.py` | 单个任务/步骤执行器 |
| BrowserPool | `src/browser_pool.py` | 浏览器池管理 |
| Scheduler | `src/scheduler.py` | 定时任务调度器 |
| Reporter | `src/reporter.py` | 执行报告生成器 |
| DataStore | `src/data_store.py` | 任务间数据共享存储 |
| Extractor | `src/extractor.py` | 页面数据提取器 |

---

## 3. YAML 任务格式

### 3.1 整体结构

```yaml
version: "1.0"
name: "任务名称"
description: "任务描述"

config:
  browser:
    type: chromium
    headless: true
    timeout: 30000
    viewport: { width: 1280, height: 720 }
  retry:
    max_attempts: 3
    delay: 2000
  screenshot:
    on_error: true
    on_success: false
    dir: "./screenshots"

variables:
  base_url: "https://example.com"
  username: "test@example.com"

datasources:
  users:
    type: csv
    path: "./data/users.csv"

tasks:
  - id: step_01
    name: "打开首页"
    action: navigate
    args:
      url: "${base_url}/home"
    screenshot: true

  - id: step_02
    name: "登录"
    action: fill
    args:
      selector: "#username"
      value: "${username}"
    wait: 1000

  - id: step_03
    name: "提交登录"
    action: click
    args:
      selector: "button[type=submit]"

  - id: step_04
    name: "验证登录成功"
    action: wait_for_selector
    args:
      selector: ".user-panel"
    timeout: 10000

  - id: step_05
    name: "提取用户信息"
    action: extract
    args:
      selector: ".user-name"
      field: "user_name"
    store: true

flow:
  steps:
    - task: step_01
    - task: step_02
    - task: step_03
    - task: step_04
      retry:
        max_attempts: 2
        delay: 3000
    - task: step_05
```

### 3.2 动作指令（Actions）

#### 导航类
| Action | 说明 | 关键参数 |
|--------|------|---------|
| `navigate` | 打开 URL | `url`, `wait_until` |
| `go_back` | 后退 | - |
| `go_forward` | 前进 | - |
| `reload` | 刷新页面 | - |

#### 交互类
| Action | 说明 | 关键参数 |
|--------|------|---------|
| `click` | 点击元素 | `selector`, `button`, `modifiers` |
| `fill` | 填写输入框 | `selector`, `value` |
| `type` | 逐字输入 | `selector`, `value`, `delay` |
| `select` | 下拉选择 | `selector`, `value`/`label`/`index` |
| `check` | 勾选复选框 | `selector` |
| `uncheck` | 取消勾选 | `selector` |
| `hover` | 悬停 | `selector` |
| `press` | 按键 | `selector`, `key` |
| `upload` | 文件上传 | `selector`, `files` |

#### 等待类
| Action | 说明 | 关键参数 |
|--------|------|---------|
| `wait` | 等待（ms） | `ms` |
| `wait_for_selector` | 等待元素出现 | `selector`, `timeout` |
| `wait_for_url` | 等待 URL 匹配 | `pattern`, `timeout` |
| `wait_for_navigation` | 等待导航完成 | `timeout` |

#### 数据提取类
| Action | 说明 | 关键参数 |
|--------|------|---------|
| `extract` | 提取文本/属性 | `selector`, `attr`, `field` |
| `extract_all` | 批量提取 | `selector`, `fields` |
| `screenshot` | 截图 | `selector`, `full_page`, `path` |

### 3.3 循环控制

```yaml
# 固定次数循环
- id: loop_test
  name: "循环3次"
  loop:
    count: 3
    tasks:
      - task: step_01

# 遍历数据
- id: batch_login
  loop:
    datasource: users
    variable: user
    tasks:
      - action: fill
        args:
          selector: "#username"
          value: "{{ user.username }}"
      - action: fill
        args:
          selector: "#password"
          value: "{{ user.password }}"
```

### 3.4 条件分支

```yaml
- id: check_status
  if:
    expression: "${status_code} == 200"
    then:
      - task: step_success
    else:
      - task: step_error
```

### 3.5 子任务

```yaml
tasks:
  - id: common_login
    is_subtask: true
    tasks:
      - action: fill
        args: { selector: "#username", value: "${username}" }
      - action: click
        args: { selector: "button[type=submit]" }

  - id: main_flow
    flow:
      steps:
        - subtask: common_login
          vars:
            username: "user1@test.com"
```

### 3.6 定时任务

```yaml
scheduler:
  enabled: true
  timezone: "Asia/Shanghai"
  jobs:
    - id: "daily_report"
      name: "每日数据报告"
      cron: "0 9 * * *"
      workflow: "./workflows/daily_report.yaml"
      enabled: true

    - id: "every_5min_check"
      name: "每5分钟健康检查"
      interval: 300
      workflow: "./workflows/health_check.yaml"
      enabled: true
```

---

## 4. 执行引擎设计

### 4.1 流程执行器（FlowRunner）
处理顺序执行、循环、条件分支、子任务调用、数据源加载。

### 4.2 浏览器池（BrowserPool）
- Chromium / WebKit / Firefox 三引擎
- 上下文池化复用
- 自动清理崩溃实例

### 4.3 数据存储（DataStore）
```python
store.set("user_count", 100)
store.render("${user_count} 条数据")  # "100 条数据"
```

---

## 5. 目录结构

```
yaml-playwright-automation/
├── src/
│   ├── __init__.py
│   ├── cli.py                  # CLI 入口
│   ├── parser.py               # YAML + Pydantic 校验
│   ├── browser_pool.py          # 浏览器池
│   ├── flow_runner.py           # 流程引擎
│   ├── task_executor.py         # 步骤执行器
│   ├── data_store.py           # 变量存储
│   ├── scheduler.py            # APScheduler 调度
│   └── actions/
│       └── navigation.py       # 18 种动作实现
├── workflows/
│   └── examples/
│       ├── login_demo.yaml
│       └── batch_extract.yaml
├── data/
├── screenshots/
├── reports/
├── pyproject.toml
├── README.md
└── DESIGN.md
```

---

## 6. 使用方法

```bash
# 安装
pip install -e .
playwright install chromium

# 运行
yamlplaywright run workflows/examples/login_demo.yaml
yamlplaywright run workflows/examples/login_demo.yaml --var username=admin --no-headless

# 校验
yamlplaywright validate workflows/examples/login_demo.yaml
yamlplaywright list ./workflows/

# 报告
yamlplaywright report reports/run_20260101.json
```

---

## 7. 技术栈

| 依赖 | 用途 |
|------|------|
| `playwright` | 浏览器自动化 |
| `pyyaml` | YAML 解析 |
| `pydantic` | 配置校验 |
| `jinja2` | 模板渲染 |
| `rich` | CLI 彩色输出 |
| `click` | CLI 框架 |
| `apscheduler` | 定时调度 |

---

*文档版本：1.0.0 | 最后更新：2026-03-24*
