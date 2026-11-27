"""Детерминированный линтер формулировок.

Находит в тексте типовые «маркеры дефектов» (размытые слова, заглушки,
незаполненные поля шаблона). Результаты не попадают в отчёт как нарушения
напрямую: они передаются модели как подсказки и выводятся в приложении
отчёта. Нарушением сигнал становится только после подтверждения моделью.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .document import Document


@dataclass
class LintHit:
    line: int
    rule: str
    fragment: str
    hint: str


# (код правила, regex, подсказка)
_RULES: list[tuple[str, re.Pattern, str]] = [
    ("vague", re.compile(
        r"\b(быстр\w*|своевременн\w*|удобн\w*|оптимальн\w*|достаточн\w*|эффективн\w*|"
        r"надлежащ\w*|соответствующ\w*|интуитивн\w*|гибк\w*|надёжн\w*|надежн\w*|"
        r"современн\w*|простой|просто|легко|обычно|как правило|по возможности|"
        r"при необходимости|максимально|минимально|некотор\w*|различн\w*|"
        r"user[- ]friendly|fast|easy|appropriate|adequate|etc)\b", re.I),
     "Размытая формулировка: нет измеримого критерия."),
    ("open_list", re.compile(r"(и т\.\s?д\.|и т\.\s?п\.|и др\.|и далее|и прочее|\.\.\.)", re.I),
     "Открытый перечень: состав не определён."),
    ("weak_modal", re.compile(r"\b(может|могут|желательно|рекомендуется|допускается|по желанию)\b", re.I),
     "Необязательная модальность: неясно, обязательно ли поведение."),
    ("placeholder", re.compile(r"\b(TBD|TODO|TBA|FIXME|XXX)\b|\?\?\?|<\s*[^>]{0,20}\s*>"),
     "Заглушка вместо значения."),
    ("to_be_filled", re.compile(r"(заполня\w+ (позже|тестировщик\w*|аналитик\w*)|будет (определ|уточн)\w*|"
                                r"уточня\w+|не заполнен\w*|отметки не проставлены)", re.I),
     "Раздел не заполнен / отложен."),
    ("empty_value", re.compile(r"\|\s*[—–-]\s*\||:\s*[—–]\s*\.?\s*(\||$)|\|\s*\|\s*\|"),
     "Пустое значение поля (прочерк или пустая ячейка)."),
    ("unfilled_choice", re.compile(r"Да\s*/\s*Нет"),
     "Не выбран вариант в чек-листе шаблона."),
    ("pronoun_ref", re.compile(r"^\s*(Это|Он[оа]?|Они)\s", re.I),
     "Местоимение в начале требования: неясный референт."),
]


def lint(doc: Document) -> list[LintHit]:
    hits: list[LintHit] = []
    for l in doc.lines:
        text = l.text
        if not text.strip():
            continue
        for code, rx, hint in _RULES:
            for m in rx.finditer(text):
                frag = m.group(0).strip(" |")
                hits.append(LintHit(l.no, code, frag or m.group(0), hint))
                break  # одно срабатывание правила на строку достаточно
    return hits


def hints_for_lines(hits: list[LintHit], start: int, end: int) -> list[LintHit]:
    return [h for h in hits if start <= h.line <= end]


def format_hints(hits: list[LintHit]) -> str:
    if not hits:
        return "(нет)"
    return "\n".join(f"- L{h.line:04d} [{h.rule}] «{h.fragment}» — {h.hint}" for h in hits)
