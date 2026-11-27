"""Устойчивый разбор JSON из ответа модели."""
from __future__ import annotations

import json
import re
from typing import Any


def parse_json(text: str) -> Any:
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    # ищем самый внешний объект/массив
    for open_c, close_c in (("{", "}"), ("[", "]")):
        s, e = t.find(open_c), t.rfind(close_c)
        if s != -1 and e > s:
            chunk = t[s:e + 1]
            try:
                return json.loads(chunk)
            except json.JSONDecodeError:
                # частая ошибка моделей — висячие запятые
                cleaned = re.sub(r",\s*([}\]])", r"\1", chunk)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    continue
    raise ValueError("Ответ модели не содержит валидного JSON")


def as_list(v: Any) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def as_int(v: Any, default: int = 0) -> int:
    try:
        if isinstance(v, str):
            m = re.search(r"\d+", v)
            return int(m.group(0)) if m else default
        return int(v)
    except (TypeError, ValueError):
        return default
