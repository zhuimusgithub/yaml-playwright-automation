"""BrowserPool - Playwright 浏览器池管理，优先使用本机浏览器."""
from __future__ import annotations

import asyncio
import os
import uuid
from typing import Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from .parser import BrowserConfig


class BrowserPool:
    """浏览器池：管理多浏览器实例和上下文."""

    def __init__(self, config: BrowserConfig) -> None:
        self.config = config
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._contexts: dict[str, BrowserContext] = {}
        self._lock = asyncio.Lock()

    async def launch(self) -> None:
        """启动 Playwright 和浏览器."""
        if self._pw is not None:
            return
        self._pw = await async_playwright().start()

        # ── 优先尝试本机已安装的浏览器 ────────────────────────────────
        local_path = self._find_browser_executable("chrome")
        if local_path:
            try:
                self._browser = await self._pw.chromium.launch(
                    executable_path=local_path,
                    headless=self.config.headless,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
                return
            except Exception:
                pass  # fallback 到内置 chromium

        # fallback: Playwright 内置 chromium
        self._browser = await getattr(self._pw, self.config.type).launch(
            headless=self.config.headless,
        )

    def _find_browser_executable(self, name: str) -> str | None:
        """查找本机浏览器路径."""
        locations: dict[str, list[str]] = {
            "chrome": [
                os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Users\zz\AppData\Local\Google\Chrome\Application\chrome.exe",
            ],
            "msedge": [
                os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                r"C:\Users\zz\AppData\Local\Microsoft\Edge\Application\msedge.exe",
            ],
            "firefox": [
                os.path.expandvars(r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe"),
                r"C:\Program Files\Mozilla Firefox\firefox.exe",
                r"C:\Users\zz\AppData\Local\Mozilla Firefox\firefox.exe",
            ],
        }

        for path in locations.get(name, []):
            if os.path.isfile(path):
                return path
        return None

    async def close(self) -> None:
        """关闭所有浏览器实例."""
        async with self._lock:
            for ctx in list(self._contexts.values()):
                await ctx.close()
            self._contexts.clear()
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._pw:
                await self._pw.stop()
                self._pw = None

    async def acquire_context(self, context_id: str | None = None) -> BrowserContext:
        """获取或创建一个浏览器上下文."""
        await self.launch()
        cid = context_id or str(uuid.uuid4())
        if cid in self._contexts:
            return self._contexts[cid]

        udd = self.config.user_data_dir
        ctx = await self._browser.new_context(
            viewport=self.config.viewport,
            ignore_https_errors=True,
            user_data_dir=udd if udd and os.path.exists(udd) else None,
        )
        self._contexts[cid] = ctx
        return ctx

    async def release_context(self, context_id: str) -> None:
        if context_id in self._contexts:
            await self._contexts[context_id].close()
            del self._contexts[context_id]

    async def new_page(self, context_id: str | None = None) -> tuple[str, Page]:
        """创建新页面，返回 (context_id, page)."""
        ctx = await self.acquire_context(context_id)
        page = await ctx.new_page()
        if self.config.timeout:
            page.set_default_timeout(self.config.timeout)
        return context_id or "default", page

    async def screenshot_page(
        self,
        page: Page,
        path: str | None = None,
        full_page: bool = False,
        selector: str | None = None,
    ) -> bytes:
        """截取页面/元素."""
        if path:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        if selector:
            return await page.locator(selector).screenshot(path=path)
        return await page.screenshot(path=path, full_page=full_page)

    async def __aenter__(self) -> "BrowserPool":
        await self.launch()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()
