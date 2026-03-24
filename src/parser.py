"""Parser - YAML 解析 + Pydantic Schema 校验."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class BrowserConfig(BaseModel):
    type: Literal["chromium", "webkit", "firefox"] = "chromium"
    headless: bool = True
    timeout: int = 30000
    viewport: dict[str, int] = Field(default_factory=lambda: {"width": 1280, "height": 720})
    user_data_dir: str | None = None
    proxy: str | None = None


class RetryConfig(BaseModel):
    max_attempts: int = 3
    delay: int = 2000  # ms


class ScreenshotConfig(BaseModel):
    on_error: bool = True
    on_success: bool = False
    dir: str = "./screenshots"


class GlobalConfig(BaseModel):
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    screenshot: ScreenshotConfig = Field(default_factory=ScreenshotConfig)


class TaskStep(BaseModel):
    id: str | None = None
    name: str | None = None
    action: str
    args: dict[str, Any] = Field(default_factory=dict)
    selector: str | None = None
    value: Any = None
    attr: str | None = None
    field: str | None = None
    wait: int | None = None
    wait_until: str | None = None
    wait_for_navigation: bool = False
    timeout: int | None = None
    screenshot: bool = False
    full_page: bool = False
    store: bool = False
    retry: RetryConfig | None = None
    is_subtask: bool = False
    vars: dict[str, Any] = Field(default_factory=dict)


class FlowStep(BaseModel):
    task: str | None = None
    subtask: str | None = None
    retry: RetryConfig | None = None
    vars: dict[str, Any] = Field(default_factory=dict)
    loop: dict[str, Any] | None = None
    parallel: list[dict] | None = None


class ScheduledJob(BaseModel):
    id: str
    name: str | None = None
    workflow: str | None = None
    cron: str | None = None
    interval: int | None = None  # seconds
    enabled: bool = True
    run_on_startup: bool = False


class SchedulerConfig(BaseModel):
    enabled: bool = False
    timezone: str = "Asia/Shanghai"
    jobs: list[ScheduledJob] = Field(default_factory=list)


class Workflow(BaseModel):
    version: str = "1.0"
    name: str = ""
    description: str = ""
    config: GlobalConfig = Field(default_factory=GlobalConfig)
    variables: dict[str, Any] = Field(default_factory=dict)
    datasources: dict[str, dict[str, Any]] = Field(default_factory=dict)
    tasks: list[dict[str, Any]] = Field(default_factory=list)
    flow: dict[str, Any] = Field(default_factory=dict)
    scheduler: SchedulerConfig | None = None


def parse_workflow(path: str) -> Workflow:
    """从文件加载并解析 YAML 工作流."""
    import yaml
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return Workflow(**raw)
