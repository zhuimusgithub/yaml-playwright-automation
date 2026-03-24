"""FlowRunner - 流程执行引擎，支持循环和条件分支."""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import re
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .browser_pool import BrowserPool
from .data_store import DataStore
from .parser import Workflow
from .task_executor import TaskExecutor

logger = logging.getLogger(__name__)
console = Console()


class FlowRunner:
    def __init__(self, workflow: Workflow, pool: BrowserPool) -> None:
        self.workflow = workflow
        self.pool = pool
        self.data = DataStore()
        for k, v in workflow.variables.items():
            self.data.set(k, v)
        self._task_map: dict[str, dict[str, Any]] = {
            t.get("id") or str(i): t for i, t in enumerate(workflow.tasks)
        }
        self._page: Any = None
        self._executor: TaskExecutor | None = None
        self._running = False

    async def run(self) -> dict[str, Any]:
        self._running = True
        console.rule(f"[bold blue]{self.workflow.name or 'YAMLPy Workflow'}")
        console.print(f"[dim]{self.workflow.description or ''}\n")

        _, self._page = await self.pool.new_page()
        self._executor = TaskExecutor(
            pool=self.pool,
            data=self.data,
            workflow=self.workflow,
            page=self._page,
            config={},
        )

        try:
            flow_steps = self.workflow.flow.get("steps", [])
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task_id = progress.add_task("执行中...", total=None)
                for i, step_ref in enumerate(flow_steps):
                    if not self._running:
                        break
                    progress.update(task_id, description=f"步骤 {i+1}/{len(flow_steps)}")
                    await self._run_step_ref(step_ref)

            if self._executor:
                console.print()
                console.print(self._executor.get_summary_table())
        finally:
            await self._cleanup()

        return {
            "status": "success",
            "steps": len(flow_steps),
            "data": self.data.to_dict(),
        }

    async def _run_step_ref(self, ref: dict[str, Any]) -> Any:
        # 条件跳过
        if "if" in ref:
            expr = ref["if"].get("expression", "")
            if not self._eval_condition(expr):
                console.print(f"  [dim]⏭  条件跳过: {expr}")
                return None

        # 循环
        if "loop" in ref:
            return await self._run_loop(ref["loop"])

        # 子任务
        if "subtask" in ref:
            subtask_id = ref["subtask"]
            overrides = ref.get("vars", {})
            saved = {k: self.data.get(k) for k in overrides}
            for k, v in overrides.items():
                self.data.set(k, self.data.render_value(v))
            result = await self._run_task(subtask_id)
            for k in saved:
                self.data.set(k, saved[k])
            return result

        # 普通任务引用
        task_id = ref.get("task")
        if task_id:
            return await self._run_task(task_id)

        return None

    async def _run_task(self, task_id: str) -> Any:
        task = self._task_map.get(task_id)
        if not task:
            console.print(f"[red]⚠  Task not found: {task_id}")
            return None
        sub_steps = task.get("tasks", [])
        if sub_steps:
            for s in sub_steps:
                await self._execute_step(s)
        else:
            await self._execute_step(task)

    async def _execute_step(self, step: dict[str, Any]) -> Any:
        if self._executor is None:
            raise RuntimeError("Executor not initialized")
        action_name = step.get("action") or step.get("name", "unknown")
        step_id = step.get("id", "")
        console.print(f"  ▶ {action_name} [{step_id}]")
        result = await self._executor.execute(step)
        if result.success:
            console.print(f"    [green]✓ done")
        else:
            console.print(f"    [red]✗ {result.error or 'failed'}")
        return result

    async def _run_loop(self, loop_cfg: dict[str, Any]) -> list[Any]:
        var_name = loop_cfg.get("variable", "item")
        mode = (
            "datasource"
            if "datasource" in loop_cfg
            else "items"
            if "items" in loop_cfg
            else "count"
        )

        if mode == "count":
            count = loop_cfg.get("count", 1)
            items = list(range(count))
        elif mode == "items":
            items = loop_cfg.get("items", [])
        else:
            ds_name = loop_cfg.get("datasource")
            ds = self.workflow.datasources.get(ds_name, {})
            items = self._load_datasource(ds)

        results = []
        for idx, item in enumerate(items):
            console.print(f"  [dim]↻ Loop {idx+1}/{len(items)}")
            self.data.set(var_name, item)
            if isinstance(item, dict):
                for k, v in item.items():
                    self.data.set(k, v)
            for step in loop_cfg.get("tasks", []):
                r = await self._run_step_ref(step)
                results.append(r)
        return results

    def _load_datasource(self, ds: dict[str, Any]) -> list[dict]:
        ds_type = ds.get("type", "csv")
        path = ds.get("path", "")
        items: list[dict] = []
        if ds_type == "csv" and path:
            try:
                with open(path, newline="", encoding="utf-8") as f:
                    items = list(csv.DictReader(f))
            except FileNotFoundError:
                console.print(f"[yellow]⚠  CSV not found: {path}")
        elif ds_type == "json" and path:
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                    items = data if isinstance(data, list) else [data]
            except FileNotFoundError:
                console.print(f"[yellow]⚠  JSON not found: {path}")
        return items

    def _eval_condition(self, expression: str) -> bool:
        if not expression:
            return True
        ev = expression
        for m in re.finditer(r'\$\{([^}]+)\}', ev):
            key = m.group(1)
            val = self.data.get(key, m.group(0))
            ev = ev.replace(m.group(0), repr(val))
        try:
            return bool(eval(ev))  # noqa: S307
        except Exception:
            return False

    async def _cleanup(self) -> None:
        if self._page:
            await self._page.close()
        self._running = False
