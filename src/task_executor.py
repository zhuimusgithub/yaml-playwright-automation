"""TaskExecutor - 单个步骤/任务执行器."""
from __future__ import annotations

import asyncio
import logging
import os
import traceback
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.table import Table

from .actions import run_action
from .browser_pool import BrowserPool
from .data_store import DataStore
from .parser import RetryConfig, Workflow

logger = logging.getLogger(__name__)
console = Console()


class ExecutionResult:
    def __init__(
        self,
        step_id: str,
        success: bool,
        result: Any = None,
        error: str | None = None,
        duration_ms: float = 0,
    ) -> None:
        self.step_id = step_id
        self.success = success
        self.result = result
        self.error = error
        self.duration_ms = duration_ms


class TaskExecutor:
    def __init__(
        self,
        pool: BrowserPool,
        data: DataStore,
        workflow: Workflow,
        page: Any,
        config: dict[str, Any],
    ) -> None:
        self.pool = pool
        self.data = data
        self.workflow = workflow
        self.page = page
        self.config = config
        self._step_results: list[ExecutionResult] = []

    def _get_retry(self, step: dict[str, Any]) -> RetryConfig:
        raw = step.get("retry")
        if not raw:
            return RetryConfig()
        if isinstance(raw, dict):
            return RetryConfig(**raw)
        return RetryConfig()

    async def _execute_step_with_retry(self, step: dict[str, Any]) -> ExecutionResult:
        retry = self._get_retry(step)
        last_error: str | None = None
        for attempt in range(1, retry.max_attempts + 1):
            t0 = asyncio.get_event_loop().time()
            try:
                result = await self._execute_step(step)
                duration = (asyncio.get_event_loop().time() - t0) * 1000
                return ExecutionResult(
                    step_id=step.get("id", step.get("action", "unknown")),
                    success=True,
                    result=result,
                    duration_ms=duration,
                )
            except Exception as e:
                last_error = traceback.format_exc()
                logger.warning(
                    "Step %s failed (attempt %d/%d): %s",
                    step.get("id", step.get("action")),
                    attempt,
                    retry.max_attempts,
                    e,
                )
                if attempt < retry.max_attempts:
                    await asyncio.sleep(retry.delay / 1000)

        return ExecutionResult(
            step_id=step.get("id", step.get("action", "unknown")),
            success=False,
            error=last_error,
            duration_ms=0,
        )

    async def _execute_step(self, step: dict[str, Any]) -> Any:
        action = step.get("action")
        if not action:
            raise ValueError(f"Step missing action: {step}")

        args = self.data.render_value(step.get("args", {}))
        selector = self.data.render_value(step.get("selector"))
        value = self.data.render_value(step.get("value"))

        if selector and "selector" not in args:
            args["selector"] = selector
        if value is not None and "value" not in args:
            args["value"] = value

        cfg = {
            "wait": step.get("wait"),
            "wait_for_navigation": step.get("wait_for_navigation", False),
            "timeout": step.get("timeout"),
            "screenshot": step.get("screenshot", False),
            "full_page": step.get("full_page", False),
        }

        result = await run_action(
            action=action,
            page=self.page,
            args=args,
            data=self.data,
            pool=self.pool,
            config=cfg,
        )

        # 存储提取结果
        if step.get("store") and result:
            if isinstance(result, dict):
                for k, v in result.items():
                    self.data.set(k, v)
            elif isinstance(result, list):
                self.data.set(step.get("field", "results"), result)

        # 截图
        sc_dir = self.workflow.config.screenshot.dir
        should_sc = step.get("screenshot") or (
            self.workflow.config.screenshot.on_error and result is None
        )
        if should_sc and self.pool:
            os.makedirs(sc_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            sc_path = os.path.join(sc_dir, f"{step.get('id', action)}_{ts}.png")
            await self.pool.screenshot_page(
                self.page, path=sc_path, full_page=cfg.get("full_page", False)
            )
            logger.info("Screenshot saved: %s", sc_path)

        return result

    async def execute(self, step: dict[str, Any]) -> ExecutionResult:
        result = await self._execute_step_with_retry(step)
        self._step_results.append(result)
        return result

    def get_summary_table(self) -> Table:
        table = Table(title="执行摘要")
        table.add_column("步骤 ID", style="cyan")
        table.add_column("状态", style="green")
        table.add_column("耗时(ms)", justify="right")
        for r in self._step_results:
            status = "✅ 成功" if r.success else "❌ 失败"
            table.add_row(r.step_id, status, f"{r.duration_ms:.0f}")
        return table
