"""Привязка цитат модели к тексту документа (защита от галлюцинаций).

Каждое замечание модели должно содержать дословную цитату. Здесь цитата
ищется в документе: сначала точно, затем после нормализации (регистр, ё/е,
пробелы, markdown-разметка, типографские символы), затем нечётко рядом с
указанной моделью строкой. Найденная позиция становится ссылкой в отчёте.
Замечание без подтверждённой цитаты в основные выводы не попадает.
"""
from __future__ import annotations

import difflib
import re
from typing import Optional

from .document import Document
from .models import Location

_TRANSLATE = str.maketrans({
    "ё": "е", "Ё": "Е", "«": '"', "»": '"', "“": '"', "”": '"', "„": '"', "’": "'", "‘": "'",
    "—": "-", "–": "-", "−": "-", "→": ">", " ": " ", " ": " ", " ": " ",
})


def normalize(s: str) -> str:
    s = s.translate(_TRANSLATE).lower()
    s = re.sub(r"[*`_#|]+", " ", s)          # markdown-разметка и разделители таблиц
    s = re.sub(r"(?<=\d) (?=\d{3}\b)", "", s)  # «1 000» -> «1000»
    s = re.sub(r"\s+", " ", s)
    return s.strip(" .;:,")


def _normalize_mapped(chars: list[tuple[str, int]]) -> tuple[str, list[int]]:
    """normalize(), сохраняющая для каждого символа номер исходной строки."""
    step: list[tuple[str, int]] = []
    for ch, ln in chars:
        for c in ch.translate(_TRANSLATE).lower():
            step.append((" " if c in "*`_#|" else c, ln))
    # схлопываем пробелы
    out: list[tuple[str, int]] = []
    for c, ln in step:
        if c.isspace():
            if out and out[-1][0] == " ":
                continue
            c = " "
        out.append((c, ln))
    # «1 000» -> «1000»
    res: list[tuple[str, int]] = []
    n = len(out)
    for i, (c, ln) in enumerate(out):
        if (c == " " and res and res[-1][0].isdigit() and i + 3 < n
                and all(out[j][0].isdigit() for j in range(i + 1, i + 4))
                and (i + 4 >= n or not out[i + 4][0].isdigit())):
            continue
        res.append((c, ln))
    return "".join(c for c, _ in res), [ln for _, ln in res]


class Grounder:
    def __init__(self, doc: Document):
        self.doc = doc
        self._norm_lines = [normalize(l.text) for l in doc.lines]
        # склеиваем весь документ (с учётом переносов строк в PDF) и нормализуем с картой позиций
        chars: list[tuple[str, int]] = []
        prev = ""
        for l in doc.lines:
            t = l.text.strip()
            if not t:
                continue
            if chars:
                if re.search(r"[а-яёa-z]-$", prev) and re.match(r"[а-яёa-z]", t):
                    chars.pop()          # перенос слова: «сум-» + «ма»
                else:
                    chars.append((" ", l.no))
            chars.extend((c, l.no) for c in t)
            prev = t
        self._joined, self._pos2line = _normalize_mapped(chars)

    def locate(self, quote: str, hint_line: Optional[int] = None) -> Location:
        quote = (quote or "").strip().strip('"«»')
        if not quote:
            return self._fallback(hint_line, "")

        # 1. точное вхождение в одну строку
        hits = [l.no for l in self.doc.lines if quote in l.text]
        if hits:
            n = _closest(hits, hint_line)
            return Location(n, n, quote, True, "exact")

        # 2. нормализованное вхождение (в т.ч. через несколько строк)
        nq = normalize(quote)
        if len(nq) >= 3:
            starts = [m.start() for m in re.finditer(re.escape(nq), self._joined)]
            if starts:
                cands = [(self._pos2line[s], self._pos2line[min(s + len(nq) - 1, len(self._pos2line) - 1)])
                         for s in starts]
                s_line, e_line = min(cands, key=lambda c: abs(c[0] - hint_line) if hint_line else 0)
                return Location(s_line, e_line, quote, True, "normalized")

        # 3. если цитата — склейка через «...», проверяем каждую часть
        if "..." in quote or "…" in quote:
            pieces = [p.strip() for p in re.split(r"\.\.\.|…", quote) if len(p.strip()) >= 4]
            locs = [self.locate(p, hint_line) for p in pieces]
            if locs and all(l.grounded for l in locs):
                return Location(min(l.line_start for l in locs), max(l.line_end for l in locs), quote, True,
                                "normalized")

        # 4. нечёткое сравнение по окну строк
        best = self._fuzzy(nq, hint_line)
        if best:
            return best
        return self._fallback(hint_line, quote)

    def _fuzzy(self, nq: str, hint_line: Optional[int]) -> Optional[Location]:
        if len(nq) < 8:
            return None
        n = len(self._norm_lines)
        rng = range(1, n + 1)
        if hint_line and 1 <= hint_line <= n:
            rng = range(max(1, hint_line - 6), min(n, hint_line + 6) + 1)
        best_ratio, best = 0.0, None
        for i in rng:
            for span in (1, 2, 3):
                j = min(n, i + span - 1)
                window = " ".join(x for x in self._norm_lines[i - 1:j] if x)
                if not window:
                    continue
                # ищем подстроку окна, наиболее похожую на цитату
                sm = difflib.SequenceMatcher(None, nq, window, autojunk=False)
                m = sm.find_longest_match(0, len(nq), 0, len(window))
                coverage = m.size / len(nq)
                ratio = max(coverage, sm.ratio() if len(window) < 2 * len(nq) else 0)
                if ratio > best_ratio:
                    best_ratio, best = ratio, (i, j)
        if best and best_ratio >= 0.8:
            i, j = best
            orig = " ".join(l.text.strip() for l in self.doc.lines[i - 1:j] if l.text.strip())
            return Location(i, j, orig[:300], True, "fuzzy")
        return None

    def _fallback(self, hint_line: Optional[int], quote: str) -> Location:
        n = len(self.doc.lines)
        line = hint_line if hint_line and 1 <= hint_line <= n else 0
        return Location(line, line, quote, False, "none")


def _closest(hits: list[int], hint: Optional[int]) -> int:
    if not hint:
        return hits[0]
    return min(hits, key=lambda h: abs(h - hint))
