"""Scheduler - 定时任务调度器（基于 APScheduler）。"""
from __future__ import annotations

import logging
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .parser import SchedulerConfig, ScheduledJob

logger = logging.getLogger(__name__)


class TaskScheduler:
    def __init__(self, config: SchedulerConfig) -> None:
        self.config = config
        self._scheduler = AsyncIOScheduler(timezone=config.timezone)

    def add_job(self, job: ScheduledJob, run_func) -> None:
        job_id = job.id
        if job.cron:
            parts = job.cron.split()
            trigger = CronTrigger(
                minute=parts[0] if len(parts) > 0 else "*",
                hour=parts[1] if len(parts) > 1 else "*",
                day=parts[2] if len(parts) > 2 else "*",
                month=parts[3] if len(parts) > 3 else "*",
                day_of_week=parts[4] if len(parts) > 4 else "*",
                timezone=self.config.timezone,
            )
        elif job.interval:
            trigger = IntervalTrigger(seconds=job.interval)
        else:
            logger.warning("Job %s has no cron or interval, skipping.", job_id)
            return

        self._scheduler.add_job(
            run_func,
            trigger=trigger,
            id=job_id,
            name=job.name,
            replace_existing=True,
        )
        logger.info("Scheduled job '%s' (%s)", job.name, job_id)

    def start(self) -> None:
        self._scheduler.start()
        logger.info("Scheduler started")

    def stop(self) -> None:
        self._scheduler.shutdown()
        logger.info("Scheduler stopped")

    def list_jobs(self) -> list[dict]:
        jobs = self._scheduler.get_jobs()
        return [
            {
                "id": j.id,
                "name": j.name,
                "next_run": str(j.next_run_time) if j.next_run_time else None,
            }
            for j in jobs
        ]
