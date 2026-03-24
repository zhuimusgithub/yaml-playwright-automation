"""CLI - 命令行入口."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.pretty import pprint

from .browser_pool import BrowserPool
from .flow_runner import FlowRunner
from .parser import parse_workflow

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _load_workflow(path: str):
    if not os.path.exists(path):
        console.print(f"[red]File not found: {path}")
        sys.exit(1)
    try:
        wf = parse_workflow(path)
        console.print(f"[green]✓ Loaded: {wf.name or path}")
        return wf
    except Exception as e:
        console.print(f"[red]Parse error: {e}")
        sys.exit(1)


def _apply_overrides(wf, headless=None, var_overrides=None):
    if headless is not None:
        wf.config.browser.headless = headless
    if var_overrides:
        for kv in var_overrides:
            if "=" in kv:
                k, v = kv.split("=", 1)
                wf.variables[k] = v


async def _run_workflow(wf):
    pool = BrowserPool(wf.config.browser)
    try:
        async with pool:
            runner = FlowRunner(wf, pool)
            return await runner.run()
    finally:
        await pool.close()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """YAMLPy - YAML 驱动的 Playwright 网页自动化框架."""
    pass


@cli.command("run")
@click.argument("workflow_file", type=click.Path(exists=True))
@click.option("--headless/--no-headless", default=None, help="浏览器无头模式")
@click.option("--var", "-v", multiple=True, help="变量覆盖，格式: key=value")
@click.option("--output", "-o", type=click.Path(), help="结果输出到文件(JSON)")
def run(workflow_file, headless, var, output):
    """运行 YAML 工作流."""
    wf = _load_workflow(workflow_file)
    _apply_overrides(wf, headless, var)

    start = datetime.now()
    result = asyncio.run(_run_workflow(wf))
    elapsed = (datetime.now() - start).total_seconds()

    report = {
        "workflow": wf.name,
        "file": workflow_file,
        "status": result["status"],
        "steps_executed": result.get("steps", 0),
        "elapsed_seconds": elapsed,
        "data": result.get("data", {}),
        "timestamp": start.isoformat(),
    }

    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        console.print(f"[green]✓ 报告已保存: {output}")

    console.print(
        Panel(
            f"状态: {result['status']} | 步骤: {result.get('steps', 0)} | 耗时: {elapsed:.1f}s"
        )
    )
    if var:
        console.print("[bold]提取的数据:[/bold]")
        pprint(result.get("data", {}))


@cli.command("validate")
@click.argument("workflow_file", type=click.Path(exists=True))
def validate(workflow_file):
    """校验 YAML 语法和 Schema."""
    try:
        wf = parse_workflow(workflow_file)
        console.print("[green]✓ 校验通过")
        console.print(
            Panel(
                f"名称: {wf.name}\n"
                f"描述: {wf.description}\n"
                f"任务数: {len(wf.tasks)}\n"
                f"流程步骤: {len(wf.flow.get('steps', []))}"
            )
        )
    except Exception as e:
        console.print(f"[red]✗ 校验失败: {e}")
        sys.exit(1)


@cli.command("list")
@click.argument(
    "workflows_dir", type=click.Path(exists=True), default="./workflows"
)
def list_workflows(workflows_dir):
    """列出工作流目录下的所有 YAML 文件."""
    files = list(Path(workflows_dir).rglob("*.yaml")) + list(
        Path(workflows_dir).rglob("*.yml")
    )
    if not files:
        console.print("[yellow]未找到任何 YAML 工作流文件")
        return
    for f in files:
        rel = f.relative_to(workflows_dir)
        try:
            wf = parse_workflow(str(f))
            console.print(
                f"  [cyan]{rel}[/cyan]  — {wf.name or '(无名称)'} ({len(wf.tasks)} 任务)"
            )
        except Exception:
            console.print(f"  [cyan]{rel}[/cyan]  [red](解析失败)")


@cli.command("report")
@click.argument("report_file", type=click.Path(exists=True))
def report(report_file):
    """查看执行报告."""
    with open(report_file, encoding="utf-8") as f:
        data = json.load(f)
    console.print(
        Panel(
            f"工作流: {data.get('workflow')}\n"
            f"状态: {data.get('status')}\n"
            f"耗时: {data.get('elapsed_seconds', 0):.1f}s"
        )
    )
    console.print("[bold]提取的数据:[/bold]")
    pprint(data.get("data", {}))


def main():
    cli(prog_name="yamlplaywright")


if __name__ == "__main__":
    main()
