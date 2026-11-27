"""Чтение входного документа и сквозная нумерация строк.

Поддерживаемые форматы: PDF, Markdown, TXT, DOCX, HTML.
Каждая строка получает глобальный номер (1..N) — именно на него ссылаются
все замечания отчёта. Для PDF дополнительно запоминается номер страницы.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Line:
    no: int                 # глобальный номер строки, 1-based
    text: str
    page: Optional[int] = None


@dataclass
class Document:
    path: Path
    fmt: str
    lines: list[Line]
    sha256: str
    title: str = ""
    sections: dict[int, str] = field(default_factory=dict)  # номер строки -> путь раздела

    # ------------------------------------------------------------------ helpers
    @property
    def name(self) -> str:
        return self.path.name

    def text(self) -> str:
        return "\n".join(l.text for l in self.lines)

    def numbered(self, start: int = 1, end: Optional[int] = None) -> str:
        """Текст с номерами строк — так документ видит модель."""
        end = end or len(self.lines)
        out = []
        for l in self.lines[start - 1:end]:
            prefix = f"L{l.no:04d}"
            if l.page is not None:
                prefix += f" p{l.page}"
            out.append(f"{prefix}| {l.text}")
        return "\n".join(out)

    def line(self, no: int) -> str:
        if 1 <= no <= len(self.lines):
            return self.lines[no - 1].text
        return ""

    def section_of(self, no: int) -> str:
        return self.sections.get(no, "")

    def location_label(self, start: int, end: Optional[int] = None) -> str:
        end = end or start
        rng = f"строка {start}" if start == end else f"строки {start}–{end}"
        if 1 <= start <= len(self.lines) and self.lines[start - 1].page is not None:
            return f"стр. {self.lines[start - 1].page}, {rng}"
        return rng


# ---------------------------------------------------------------------- loading
SUPPORTED = {".pdf", ".md", ".markdown", ".txt", ".docx", ".html", ".htm"}


def load_document(path: str | Path) -> Document:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Файл требований не найден: {path}")
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        raise ValueError(f"Формат {ext} не поддерживается. Поддерживаются: {', '.join(sorted(SUPPORTED))}")

    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()

    if ext == ".pdf":
        lines = _read_pdf(path)
        fmt = "pdf"
    elif ext == ".docx":
        lines = [Line(0, t) for t in _read_docx(path)]
        fmt = "docx"
    elif ext in (".html", ".htm"):
        lines = [Line(0, t) for t in _read_html(raw.decode("utf-8", errors="replace"))]
        fmt = "html"
    else:
        lines = [Line(0, t) for t in _decode(raw).splitlines()]
        fmt = "markdown" if ext in (".md", ".markdown") else "text"

    lines = _clean(lines)
    for i, l in enumerate(lines, 1):
        l.no = i
    if not any(l.text.strip() for l in lines):
        raise ValueError(
            "Не удалось извлечь текст из документа. Если это скан PDF — нужен текстовый слой (OCR)."
        )

    doc = Document(path=path, fmt=fmt, lines=lines, sha256=sha)
    doc.sections = _detect_sections(lines)
    doc.title = _detect_title(lines) or path.stem
    return doc


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _clean(lines: list[Line]) -> list[Line]:
    out: list[Line] = []
    for l in lines:
        t = l.text.replace(" ", " ").replace(" ", " ").replace("\t", "    ").rstrip()
        l.text = t
        out.append(l)
    # схлопываем серии пустых строк (оставляем одну), чтобы нумерация была компактной
    compact: list[Line] = []
    for l in out:
        if not l.text.strip() and compact and not compact[-1].text.strip():
            continue
        compact.append(l)
    while compact and not compact[0].text.strip():
        compact.pop(0)
    while compact and not compact[-1].text.strip():
        compact.pop()
    return compact


def _read_pdf(path: Path) -> list[Line]:
    lines: list[Line] = []
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(str(path)) as pdf:
            for pno, page in enumerate(pdf.pages, 1):
                lines.extend(Line(0, t, pno) for t in _pdf_page_lines(page))
        if any(l.text.strip() for l in lines):
            return lines
    except ImportError:
        pass

    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        for pno, page in enumerate(reader.pages, 1):
            for t in (page.extract_text() or "").splitlines():
                lines.append(Line(0, t, pno))
        if any(l.text.strip() for l in lines):
            return lines
    except ImportError:
        pass

    if shutil.which("pdftotext"):
        res = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
        for pno, page_text in enumerate(res.stdout.split("\f"), 1):
            for t in page_text.splitlines():
                lines.append(Line(0, t, pno))
        return lines

    raise RuntimeError("Для чтения PDF установите pdfplumber или pypdf: pip install -r requirements.txt")


def _pdf_page_lines(page) -> list[str]:
    """Текст страницы, где таблицы собраны построчно в виде «| ячейка | ячейка |»."""
    try:
        tables = page.find_tables()
    except Exception:  # noqa: BLE001
        tables = []
    boxes = [t.bbox for t in tables]

    def inside(obj) -> bool:
        x = (obj["x0"] + obj["x1"]) / 2
        y = (obj["top"] + obj["bottom"]) / 2
        return any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in boxes)

    items: list[tuple[float, str]] = []
    try:
        for tl in page.extract_text_lines(layout=False, strip=True):
            if not inside(tl):
                items.append((tl["top"], tl["text"]))
    except Exception:  # noqa: BLE001
        return (page.extract_text() or "").splitlines()
    for t in tables:
        top = t.bbox[1]
        for i, row in enumerate(t.extract()):
            cells = [" ".join((c or "").split()) for c in row]
            items.append((top + i * 0.01, "| " + " | ".join(cells) + " |"))
    items.sort(key=lambda it: it[0])
    return [text for _, text in items]


def _read_docx(path: Path) -> list[str]:
    try:
        import docx  # type: ignore
    except ImportError as e:
        raise RuntimeError("Для чтения DOCX установите python-docx: pip install python-docx") from e

    d = docx.Document(str(path))
    out: list[str] = []
    body = d.element.body
    for child in body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            p = docx.text.paragraph.Paragraph(child, d)
            style = (p.style.name or "").lower() if p.style is not None else ""
            text = p.text
            m = re.match(r"heading (\d)", style)
            if m and text.strip():
                text = "#" * int(m.group(1)) + " " + text
            elif "list" in style and text.strip():
                text = "* " + text
            out.append(text)
        elif tag == "tbl":
            t = docx.table.Table(child, d)
            for row in t.rows:
                cells = [c.text.replace("\n", " ").strip() for c in row.cells]
                out.append("| " + " | ".join(cells) + " |")
            out.append("")
    return out


def _read_html(html: str) -> list[str]:
    html = re.sub(r"(?is)<(script|style).*?</\1>", "", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|li|tr|h\d|table)>", "\n", html)
    html = re.sub(r"(?i)<h(\d)[^>]*>", lambda m: "\n" + "#" * int(m.group(1)) + " ", html)
    html = re.sub(r"(?i)</t[dh]>", " | ", html)
    text = re.sub(r"<[^>]+>", "", html)
    import html as h

    return h.unescape(text).splitlines()


# --------------------------------------------------------------- structure
_MD_HEADING = re.compile(r"^\s*(#{1,6})\s+(.*\S)\s*$")
_NUM_HEADING = re.compile(r"^\s*((?:\d+\.){1,4}\d*)\s+([А-ЯЁA-Z][^.]{2,80})$")
_CAPS_HEADING = re.compile(r"^\s*([А-ЯЁA-Z][А-ЯЁA-Z0-9 ,.\-]{4,80})\s*$")


def _heading(text: str) -> Optional[tuple[int, str]]:
    m = _MD_HEADING.match(text)
    if m:
        return len(m.group(1)), _strip_md(m.group(2))
    m = _NUM_HEADING.match(text)
    if m and len(text) < 90:
        level = m.group(1).rstrip(".").count(".") + 1
        return level, _strip_md(text.strip())
    return None


def _strip_md(s: str) -> str:
    return re.sub(r"[*_`]+", "", s).strip()


def _detect_sections(lines: list[Line]) -> dict[int, str]:
    stack: list[tuple[int, str]] = []
    result: dict[int, str] = {}
    for l in lines:
        h = _heading(l.text)
        if h:
            level, title = h
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
        # заголовок первого уровня (название документа) в путь не включаем
        path = [t for lv, t in stack if lv > 1] or [t for _, t in stack]
        result[l.no] = " / ".join(path)
    return result


def _detect_title(lines: list[Line]) -> str:
    for l in lines[:15]:
        h = _heading(l.text)
        if h:
            return h[1]
    for l in lines[:5]:
        if l.text.strip():
            return _strip_md(l.text.strip())[:120]
    return ""
