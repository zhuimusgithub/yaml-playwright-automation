# YAMLPy

> YAML 驱动的 Playwright 网页自动化框架

## 安装

```bash
pip install -e .
playwright install chromium
```

## 快速开始

```bash
# 运行示例工作流
yamlplaywright run workflows/examples/login_demo.yaml

# 带参数覆盖
yamlplaywright run workflows/examples/login_demo.yaml \
  --var username=admin \
  --var password=secret \
  --no-headless

# 校验 YAML
yamlplaywright validate workflows/examples/login_demo.yaml

# 列出所有工作流
yamlplaywright list ./workflows/
```

## 项目结构

```
src/
  cli.py            # CLI 入口
  parser.py         # YAML + Pydantic Schema 校验
  browser_pool.py   # Playwright 浏览器池
  flow_runner.py    # 流程执行引擎（循环/条件/子任务）
  task_executor.py  # 单步执行 + 重试 + 截图
  data_store.py     # 变量存储 + Jinja2 渲染
  scheduler.py      # APScheduler 定时调度
  actions/
    └── navigation.py  # 18 种动作实现

workflows/
  examples/
    ├── login_demo.yaml      # 基础登录流程
    └── batch_extract.yaml   # 循环 + 条件分支示例
```

详细设计文档见 [DESIGN.md](./DESIGN.md)。
