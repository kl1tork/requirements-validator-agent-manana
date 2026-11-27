"""Нарезка документа на отдельные требования.

1. Парсер правил находит явные идентификаторы (Ф-1, FR-2, REQ-10, НФТ-3 ...)
   и строит резервную нарезку по структуре (пункты списков, абзацы, строки таблиц).
2. Модель выделяет требования по всему документу (в т.ч. без номеров).
3. Результат модели проверяется: каждая цитата привязывается к строкам документа,
   пропущенные моделью пункты с явными ID добавляются из парсера.
Если модель недоступна или вернула мусор — используется резервная нарезка.
"""
from __future__ import annotations

import re
from typing import Optional

from .document import Document
from .grounding import Grounder
from .jsonutil import as_int, as_list
from .llm import LLMClient
from .models import Requirement
from . import prompts

_LIST_ITEM = re.compile(r"^\s*(?:[*\-•]|\d{1,3}[.)])\s+(.*\S)")
_TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{3,}")


def explicit_ids(doc: Document) -> dict[str, int]:
    """Идентификаторы требований вида «Ф-1», «FR-2.1» в начале пункта -> номер строки."""
    found: dict[str, int] = {}
    for l in doc.lines:
        head = l.text.strip()[:40]
        head = re.sub(r"^[*\-•\s]+", "", head)
        m = re.match(r"\**\s*((?:[A-ZА-ЯЁ]{1,6})[-_]\d{1,4}(?:\.\d{1,3})*)\.?\**", head)
        if m and m.group(1) not in found:
            found[m.group(1)] = l.no
    return found


def rule_segments(doc: Document) -> list[Requirement]:
    """Резервная нарезка без модели."""
    reqs: list[Requirement] = []
    in_code = False
    header_seen: set[int] = set()
    lines = doc.lines
    for idx, l in enumerate(lines):
        t = l.text.strip()
        if t.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not t or t.startswith("#") or set(t) <= set("-=_*"):
            continue
        if _TABLE_SEP.match(t):
            header_seen.add(idx - 1)
            continue
        if _TABLE_ROW.match(t):
            nxt = lines[idx + 1].text.strip() if idx + 1 < len(lines) else ""
            if _TABLE_SEP.match(nxt):
                continue  # шапка таблицы
            cells = [c.strip() for c in t.strip("|").split("|")]
            if not any(re.sub(r"[\s—–-]", "", c) for c in cells):
                continue
            text = " | ".join(c for c in cells if c)
        else:
            m = _LIST_ITEM.match(t)
            text = m.group(1) if m else t
        if len(re.sub(r"\W", "", text)) < 6:
            continue
        doc_id = None
        idm = re.match(r"\**\s*((?:[A-ZА-ЯЁ]{1,6})[-_]\d{1,4}(?:\.\d{1,3})*)\.?\**", text)
        if idm:
            doc_id = idm.group(1)
        clean = re.sub(r"[*`]+", "", text)
        reqs.append(Requirement(
            rid="", doc_id=doc_id, section=doc.section_of(l.no), line_start=l.no, line_end=l.no,
            quote=_clean_quote(l.text)[:300], summary=_short(clean), kind="", source="rules",
        ))
    return _renumber(reqs)


def llm_segments(doc: Document, llm: LLMClient) -> tuple[list[Requirement], list[str]]:
    notes: list[str] = []
    ids = explicit_ids(doc)
    data = llm.complete_json(prompts.SYSTEM, prompts.segmentation_prompt(doc.numbered(), list(ids)),
                             stage="нарезка")
    raw = as_list(data.get("requirements") if isinstance(data, dict) else data)
    grounder = Grounder(doc)
    reqs: list[Requirement] = []
    dropped = 0
    for item in raw:
        if not isinstance(item, dict):
            continue
        quote = str(item.get("quote") or "").strip()
        ls = as_int(item.get("line_start"))
        le = max(as_int(item.get("line_end"), ls), ls)
        loc = grounder.locate(quote, ls or None)
        if not loc.grounded:
            # цитата не найдена; если строки валидны — берём текст строк как цитату
            if 1 <= ls <= len(doc.lines) and doc.line(ls).strip():
                quote = " ".join(doc.line(i).strip() for i in range(ls, min(le, ls + 3) + 1)).strip()[:300]
            else:
                dropped += 1
                continue
        else:
            ls = loc.line_start
            le = max(le, loc.line_end) if le - ls < 15 else loc.line_end
        doc_id = item.get("doc_id")
        doc_id = str(doc_id).strip() if doc_id not in (None, "", "null", "None") else None
        reqs.append(Requirement(
            rid="", doc_id=doc_id,
            section=_pick_section(doc, ls, str(item.get("section") or "")),
            line_start=ls, line_end=le, quote=quote,
            summary=str(item.get("summary") or _short(quote)),
            kind=str(item.get("kind") or ""), source="llm",
        ))
    if dropped:
        notes.append(f"Нарезка: отброшено {dropped} элемент(ов) модели без подтверждённой цитаты.")

    # добавляем пропущенные явные ID
    have = {r.doc_id for r in reqs if r.doc_id}
    have_lines = {r.line_start for r in reqs}
    for rid_text, line in ids.items():
        if rid_text not in have and line not in have_lines:
            reqs.append(Requirement(
                rid="", doc_id=rid_text, section=doc.section_of(line), line_start=line, line_end=line,
                quote=_clean_quote(doc.line(line))[:300], summary=_short(doc.line(line)), source="rules",
            ))
            notes.append(f"Нарезка: пункт {rid_text} (строка {line}) пропущен моделью и добавлен парсером.")

    reqs.sort(key=lambda r: (r.line_start, r.line_end))
    reqs = _dedupe(reqs)
    return _renumber(reqs), notes


def segment(doc: Document, llm: Optional[LLMClient], mode: str = "llm") -> tuple[list[Requirement], list[str]]:
    if mode == "rules" or llm is None:
        return rule_segments(doc), ["Нарезка выполнена парсером правил (без модели)."]
    try:
        reqs, notes = llm_segments(doc, llm)
        if len(reqs) >= max(1, len(explicit_ids(doc))):
            return reqs, notes
        notes.append("Модель вернула слишком мало требований — использована резервная нарезка парсером.")
    except Exception as e:  # noqa: BLE001
        notes = [f"Ошибка нарезки моделью ({e}); использована резервная нарезка парсером."]
    return rule_segments(doc), notes


# ---------------------------------------------------------------- helpers
def _renumber(reqs: list[Requirement]) -> list[Requirement]:
    width = 2 if len(reqs) < 100 else 3
    for i, r in enumerate(reqs, 1):
        r.rid = f"R-{i:0{width}d}"
    return reqs


def _dedupe(reqs: list[Requirement]) -> list[Requirement]:
    out: list[Requirement] = []
    seen: set[tuple] = set()
    for r in reqs:
        key = (r.line_start, re.sub(r"\W", "", r.quote.lower())[:60])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _short(text: str, words: int = 15) -> str:
    t = re.sub(r"[*`|#]+", " ", text)
    t = re.sub(r"\s+", " ", t).strip()
    parts = t.split(" ")
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")


def _clean_quote(text: str) -> str:
    """Текст строки без маркеров списка и markdown-выделения (сам текст не меняется)."""
    t = re.sub(r"^\s*(?:[*\-•]|\d{1,3}[.)])\s+", "", text.strip())
    return t.replace("**", "").replace("`", "").strip()


def _pick_section(doc: Document, line: int, llm_section: str) -> str:
    """Для размеченных форматов раздел берём из заголовков документа, для PDF/TXT — у модели."""
    own = doc.section_of(line)
    if doc.fmt in ("markdown", "docx", "html") and own:
        return own
    return llm_section or own
