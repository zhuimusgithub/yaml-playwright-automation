"""DataStore - 全局数据存储，支持变量渲染."""
from __future__ import annotations

import re
from typing import Any
from jinja2 import Template

_DOLLAR_PATTERN = re.compile(r'\$\{([^}]+)\}')


class DataStore:
    """键值存储 + Jinja2 模板渲染."""

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def render(self, text: str) -> Any:
        """对字符串进行 Jinja2 渲染，支持 ${var} 和 {{ var }} 两种语法."""
        if not isinstance(text, str):
            return text
        try:
            # 统一转换 ${var} -> {{ var }}
            converted = _DOLLAR_PATTERN.sub(r'{{\1}}', text)
            rendered = Template(converted, autoescape=False).render(self._store)
            return self._cast(rendered)
        except Exception:
            return text

    def render_value(self, value: Any) -> Any:
        """递归渲染任意值中的变量引用."""
        if isinstance(value, str):
            return self.render(value)
        if isinstance(value, dict):
            return {k: self.render_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.render_value(item) for item in value]
        return value

    @staticmethod
    def _cast(s: str) -> Any:
        """将字符串尝试转为原生类型."""
        s = s.strip()
        if s.lower() in ("true", "false"):
            return s.lower() == "true"
        if s.lower() == "null" or s == "":
            return None
        try:
            # 先尝试 int，避免 42 被 cast 成 42.0
            if re.match(r'^-?\d+$', s):
                return int(s)
            return float(s)
        except ValueError:
            return s

    def to_dict(self) -> dict[str, Any]:
        return self._store.copy()
