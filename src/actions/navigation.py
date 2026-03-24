"""Actions - 动作实现模块."""
from __future__ import annotations

import asyncio
from typing import Any, TYPE_CHECKING

from playwright.async_api import Page, Locator

if TYPE_CHECKING:
    from ..browser_pool import BrowserPool
    from ..data_store import DataStore


# ── 工具函数 ────────────────────────────────────────────────────────────────

async def _wait_ms(ms: int) -> None:
    if ms and ms > 0:
        await asyncio.sleep(ms / 1000)


# ── 导航类 ─────────────────────────────────────────────────────────────────

async def action_navigate(page: Page, args: dict[str, Any], **kwargs: Any) -> dict:
    url = args.get("url", "")
    wait_until = args.get("wait_until", "load")
    timeout = args.get("timeout")
    await page.goto(url, wait_until=wait_until, timeout=timeout)
    return {"url": page.url, "title": await page.title()}


async def action_go_back(page: Page, **_: Any) -> None:
    await page.go_back()


async def action_go_forward(page: Page, **_: Any) -> None:
    await page.go_forward()


async def action_reload(page: Page, **_: Any) -> None:
    await page.reload()


# ── 交互类 ─────────────────────────────────────────────────────────────────

async def action_click(
    page: Page,
    args: dict[str, Any],
    wait_for_navigation: bool = False,
    timeout: int | None = None,
    **_: Any,
) -> None:
    selector = args.get("selector", "")
    button = args.get("button", "left")
    modifiers = args.get("modifiers", [])
    ms = timeout or 30000
    if wait_for_navigation:
        async with page.expect_navigation(timeout=ms):
            await page.click(selector, button=button, modifiers=modifiers)
    else:
        await page.click(selector, button=button, modifiers=modifiers)


async def action_fill(page: Page, args: dict[str, Any], data: "DataStore", **_: Any) -> None:
    selector = args.get("selector", "")
    value = data.render_value(args.get("value", ""))
    await page.fill(selector, str(value))


async def action_type(page: Page, args: dict[str, Any], data: "DataStore", **_: Any) -> None:
    selector = args.get("selector", "")
    value = data.render_value(args.get("value", ""))
    delay = args.get("delay", 0)
    await page.type(selector, str(value), delay=delay)


async def action_select(page: Page, args: dict[str, Any], data: "DataStore", **_: Any) -> None:
    selector = args.get("selector", "")
    value = data.render_value(args.get("value"))
    label = data.render_value(args.get("label"))
    index = args.get("index")
    if value is not None:
        await page.select_option(selector, value=str(value))
    elif label is not None:
        await page.select_option(selector, label=str(label))
    elif index is not None:
        await page.select_option(selector, index=int(index))


async def action_check(page: Page, args: dict[str, Any], **_: Any) -> None:
    await page.check(args.get("selector", ""))


async def action_uncheck(page: Page, args: dict[str, Any], **_: Any) -> None:
    await page.uncheck(args.get("selector", ""))


async def action_hover(page: Page, args: dict[str, Any], **_: Any) -> None:
    await page.hover(args.get("selector", ""))


async def action_press(page: Page, args: dict[str, Any], **_: Any) -> None:
    selector = args.get("selector")
    key = args.get("key", "")
    if selector:
        await page.press(selector, key)
    else:
        await page.keyboard.press(key)


async def action_upload(page: Page, args: dict[str, Any], **_: Any) -> None:
    files = args.get("files", [])
    if isinstance(files, str):
        files = [files]
    await page.set_input_files(args.get("selector", ""), files)


# ── 等待类 ─────────────────────────────────────────────────────────────────

async def action_wait(
    page: Page,
    wait: int | None = None,
    args: dict[str, Any] | None = None,
    **_: Any,
) -> None:
    ms = wait or (args or {}).get("ms", 0)
    await _wait_ms(ms)


async def action_wait_for_selector(
    page: Page,
    args: dict[str, Any],
    timeout: int | None = None,
    **_: Any,
) -> None:
    ms = timeout or 30000
    await page.wait_for_selector(args.get("selector", ""), timeout=ms)


async def action_wait_for_navigation(
    page: Page,
    timeout: int | None = None,
    args: dict[str, Any] | None = None,
    **_: Any,
) -> None:
    ms = timeout or (args or {}).get("timeout", 30000)
    await page.wait_for_load_state("networkidle", timeout=ms)


async def action_wait_for_url(
    page: Page,
    args: dict[str, Any],
    timeout: int | None = None,
    **_: Any,
) -> None:
    ms = timeout or 30000
    await page.wait_for_url(args.get("pattern", ""), timeout=ms)


# ── 数据提取类 ──────────────────────────────────────────────────────────────

async def action_extract(
    page: Page,
    args: dict[str, Any],
    store_obj: "DataStore | None" = None,
    field: str | None = None,
    **_: Any,
) -> dict | None:
    selector = args.get("selector", "")
    attr = args.get("attr", "textContent")
    fld = field or args.get("field", "")
    loc = page.locator(selector)
    count = await loc.count()
    if count == 0:
        return None
    value = await loc.first.text_content() if attr == "textContent" else await loc.first.get_attribute(attr)
    if store_obj and fld:
        store_obj.set(fld, value)
    return {fld: value} if fld else value


async def action_extract_all(
    page: Page,
    args: dict[str, Any],
    store_obj: "DataStore | None" = None,
    **_: Any,
) -> list[dict]:
    selector = args.get("selector", "")
    fields = args.get("fields", [])
    loc = page.locator(selector)
    count = await loc.count()
    results = []
    for i in range(count):
        item = {}
        for f in fields:
            sub = loc.nth(i).locator(f["selector"])
            attr = f.get("attr", "textContent")
            fld = f.get("field", "")
            val = await sub.text_content() if attr == "textContent" else await sub.get_attribute(attr)
            if fld:
                item[fld] = val
        results.append(item)
    if store_obj:
        store_obj.set(args.get("var", "extract_results"), results)
    return results


async def action_screenshot(
    page: Page,
    args: dict[str, Any],
    pool: "BrowserPool | None" = None,
    **_: Any,
) -> bytes | None:
    if pool:
        return await pool.screenshot_page(
            page,
            path=args.get("path"),
            full_page=args.get("full_page", False),
            selector=args.get("selector"),
        )
    selector = args.get("selector")
    if selector:
        return await page.locator(selector).screenshot(path=args.get("path"))
    return await page.screenshot(path=args.get("path"), full_page=args.get("full_page", False))


# ── 注册表 ─────────────────────────────────────────────────────────────────

ACTION_MAP: dict[str, Any] = {
    "navigate": action_navigate,
    "go_back": action_go_back,
    "go_forward": action_go_forward,
    "reload": action_reload,
    "click": action_click,
    "fill": action_fill,
    "type": action_type,
    "select": action_select,
    "check": action_check,
    "uncheck": action_uncheck,
    "hover": action_hover,
    "press": action_press,
    "upload": action_upload,
    "wait": action_wait,
    "wait_for_selector": action_wait_for_selector,
    "wait_for_navigation": action_wait_for_navigation,
    "wait_for_url": action_wait_for_url,
    "extract": action_extract,
    "extract_all": action_extract_all,
    "screenshot": action_screenshot,
}


async def run_action(
    action: str,
    page: Page,
    args: dict[str, Any],
    data: "DataStore",
    pool: "BrowserPool",
    config: dict[str, Any],
) -> Any:
    """执行单个动作，分发到具体实现."""
    fn = ACTION_MAP.get(action)
    if fn is None:
        raise ValueError(f"Unknown action: {action}")
    return await fn(
        page=page,
        args=args,
        data=data,
        pool=pool,
        store_obj=data,
        timeout=config.get("timeout"),
        wait=config.get("wait"),
        wait_for_navigation=config.get("wait_for_navigation", False),
        **config,
    )
