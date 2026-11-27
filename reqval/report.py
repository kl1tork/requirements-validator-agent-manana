"""Формирование отчёта (Markdown, русский язык). Также умеет HTML и JSON."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

from . import criteria as C
from .document import Document
from .lint import LintHit
from .models import Issue, Requirement, RequirementResult, RunInfo, SetResult

SHORT = {
    "necessary": "Необх.", "appropriate": "Умест.", "unambiguous": "Однозн.", "complete": "Полн.",
    "singular": "Единич.", "feasible": "Выполн.", "verifiable": "Провер.", "correct": "Коррект.",
    "conforming": "Шаблон", "traceable": "Просл.",
}
MARK = {"violation": "✖", "ok": "✔", "n/a": "—"}


def _cell(s: Any) -> str:
    return str(s if s is not None else "").replace("|", "\\|").replace("\n", " ").strip()


def _q(s: str, limit: int = 220) -> str:
    s = " ".join(str(s).split())
    if len(s) > limit:
        s = s[:limit].rstrip() + "…"
    return "«" + s.replace("«", "\"").replace("»", "\"") + "»"


class Report:
    def __init__(self, doc: Document, info: RunInfo, reqs: list[Requirement],
                 per_req: dict[str, RequirementResult], set_res: SetResult, verify_out: dict,
                 lint_hits: list[LintHit]):
        self.doc, self.info, self.reqs = doc, info, reqs
        self.per_req, self.set_res, self.verify_out, self.lint_hits = per_req, set_res, verify_out, lint_hits
        self.all_issues: list[Issue] = [i for r in per_req.values() for i in r.issues] + set_res.issues
        self.confirmed = [i for i in self.all_issues if i.status == "confirmed"]
        self.discarded = [i for i in self.all_issues if i.status != "confirmed"]

    # ----------------------------------------------------------- aggregates
    def req_status(self, rid: str) -> dict[str, str]:
        """Статус по критериям: нарушение только при подтверждённом замечании с цитатой."""
        res = self.per_req.get(rid)
        out = {}
        bad = {i.criterion for i in (res.issues if res else []) if i.status == "confirmed"}
        for code in C.INDIVIDUAL_CODES:
            if code in bad:
                out[code] = "violation"
            else:
                raw = res.criteria.get(code, "n/a") if res else "n/a"
                out[code] = "n/a" if raw == "n/a" else "ok"
        return out

    def set_status(self, code: str) -> str:
        """violation — есть подтверждённое замечание набора или отклонённое как дубликат подтверждённого;
        unconfirmed — модель сочла свойство нарушенным, но без подтверждённой цитаты (✔ ставить нельзя)."""
        if any(i.criterion == code and i.status == "confirmed" for i in self.set_res.issues) or self.set_dup_refs(code):
            return "violation"
        cv = self.set_res.criteria.get(code)
        if cv is None or cv.status == "n/a":
            return "n/a"
        return "unconfirmed" if cv.status == "violation" else "ok"

    def set_dup_refs(self, code: str) -> list[str]:
        """Подтверждённые замечания, дубликатами которых признаны отклонённые замечания набора по критерию."""
        confirmed = {i.iid for i in self.confirmed}
        refs: list[str] = []
        for i in self.set_res.issues:
            if i.criterion == code and i.status == "rejected":
                refs += [d for d in i.duplicate_of if d in confirmed and d not in refs]
        return sorted(refs, key=lambda s: int(s.split("-")[1]))

    def verdict(self) -> tuple[str, str]:
        sev = Counter(i.severity for i in self.confirmed)
        if sev["critical"]:
            return ("НЕТ — начинать разработку и тестирование по документу нельзя",
                    f"Подтверждённых критичных дефектов: {sev['critical']} (противоречия, непроверяемые или неполные "
                    f"формулировки). Реализация по ним потребует догадок, а результаты тестов нельзя будет "
                    f"однозначно оценить.")
        if sev["major"]:
            return ("УСЛОВНО — можно начинать после исправления существенных замечаний",
                    f"Критичных дефектов нет; существенных замечаний с риском неверной реализации: {sev['major']}.")
        return ("ДА — документ пригоден для начала разработки и тестирования",
                "Критичных и существенных дефектов не выявлено.")

    # ------------------------------------------------------------- render
    def markdown(self) -> str:
        out: list[str] = []
        w = out.append
        w(f"# Отчёт о проверке требований: {self.doc.title}\n")
        w("Статическое ревью требований до разработки по ISO/IEC/IEEE 29148:2018 (п. 5.2.5, 5.2.6) и "
          "IEEE Std 830-1998 (п. 4.3). Отчёт сформирован агентом «Манана» автоматически; ссылки «строка N» указывают "
          "на номер строки во входном файле.\n")

        # 1. паспорт
        i = self.info
        w("## 1. Паспорт прогона\n")
        w("| Параметр | Значение |\n| :--- | :--- |")
        rows = [
            ("Документ", f"{i.document_title} (`{i.document_name}`)"),
            ("Формат / объём", f"{self.doc.fmt}, {len(self.doc.lines)} строк"),
            ("SHA-256 документа", f"`{i.document_sha256}`"),
            ("Дата прогона", f"{i.started_at} — {i.finished_at}"),
            ("Модель", f"{i.model} (провайдер: {i.provider}, temperature = 0)"),
            ("Агент", "Манана — агент проверки требований"),
            ("Версия агента", f"`{i.agent_version}`"),
            ("Обращений к модели", f"{i.llm_calls} (+ {i.cache_hits} из кэша)"),
            ("Критерии", "ISO/IEC/IEEE 29148:2018 п. 5.2.5, 5.2.6; IEEE Std 830-1998 п. 4.3"),
        ]
        for k, v in rows:
            w(f"| {k} | {_cell(v)} |")
        if i.notes:
            w("\nЗамечания прогона:")
            for n in i.notes:
                w(f"- {n}")
        w("")

        # 2. нарезка
        w("## 2. Как агент нарезал требования\n")
        w(f"Выделено требований: **{len(self.reqs)}**. Если в документе у пункта нет номера, агент присвоил "
          "собственный идентификатор (R-NN), а в столбце «ID в документе» стоит «—»; цитата сохранена.\n")
        w("| ID в отчёте | ID в документе | Раздел | Место | Краткая формулировка | Цитата |")
        w("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in self.reqs:
            w(f"| {r.rid} | {_cell(r.doc_id or '—')} | {_cell(r.section)} | "
              f"{_cell(self.doc.location_label(r.line_start, r.line_end))} | {_cell(r.summary)} | "
              f"{_cell(_q(r.quote, 160))} |")
        w("")

        # 3. каждое требование
        w("## 3. Проверка каждого требования\n")
        w("### 3.1. Матрица соответствия критериям\n")
        w("✔ — соответствует, ✖ — нарушение (подтверждено цитатой), ? — модель отметила нарушение, но без подтверждённой цитаты, — — неприменимо.\n")
        w("Критерии: " + "; ".join(f"{SHORT[c]} — {C.name(c)} ({C.ref(c)})" for c in C.INDIVIDUAL_CODES) + ".\n")
        w("| ID | " + " | ".join(SHORT[c] for c in C.INDIVIDUAL_CODES) + " | Нарушений |")
        w("| :--- | " + " | ".join(":---:" for _ in C.INDIVIDUAL_CODES) + " | ---: |")
        for r in self.reqs:
            st = self.req_status(r.rid)
            n = sum(1 for x in self.per_req[r.rid].issues if x.status == "confirmed")
            w(f"| {r.rid} | " + " | ".join(MARK[st[c]] for c in C.INDIVIDUAL_CODES) + f" | {n} |")
        w("")
        w("### 3.2. Замечания по требованиям\n")
        for r in self.reqs:
            did = f" · {r.doc_id}" if r.doc_id else ""
            w(f"#### {r.rid}{did} — {self.doc.location_label(r.line_start, r.line_end)}\n")
            w(f"> {_q(r.quote, 400)}\n")
            issues = [x for x in self.per_req[r.rid].issues if x.status == "confirmed"]
            if not issues:
                w("Нарушений не выявлено.\n")
                continue
            for x in sorted(issues, key=lambda z: C.SEVERITY_ORDER[z.severity]):
                w(self._issue_md(x))
        # 4. набор
        w("## 4. Проверка всего набора требований\n")
        w("| Свойство набора | Пункт стандарта | Результат | Комментарий |")
        w("| :--- | :--- | :---: | :--- |")
        for code in C.SET_CODES:
            st = self.set_status(code)
            cv = self.set_res.criteria.get(code)
            n = sum(1 for x in self.set_res.issues if x.criterion == code and x.status == "confirmed")
            refs = self.set_dup_refs(code)
            res = {"violation": f"✖ ({n})" if n else "✖", "ok": "✔", "n/a": "—",
                   "unconfirmed": "? (не подтверждено цитатой)"}[st]
            if refs:
                res += " — см. " + ", ".join(refs)
            elif st != "violation" and any(x.criterion == code and x.status != "confirmed" for x in self.set_res.issues):
                res += " (замечание модели отклонено, см. прил. A)"
            w(f"| {C.name(code)} | {C.ref(code)} | {res} | {_cell(cv.comment if cv else '')} |")
        w("")
        set_issues = [x for x in self.set_res.issues if x.status == "confirmed"]
        if set_issues:
            w("### Замечания уровня набора\n")
            for x in sorted(set_issues, key=lambda z: (C.SEVERITY_ORDER[z.severity], z.iid)):
                w(self._issue_md(x, with_reqs=True))
        else:
            w("Замечаний уровня набора не выявлено.\n")

        # 5. сводка
        w("## 5. Сводка\n")
        sev = Counter(x.severity for x in self.confirmed)
        reqs_bad = {rid for rid, res in self.per_req.items() if any(x.status == "confirmed" for x in res.issues)}
        w("| Показатель | Значение |\n| :--- | ---: |")
        w(f"| Требований выделено | {len(self.reqs)} |")
        w(f"| Требований с нарушениями | {len(reqs_bad)} |")
        w(f"| Требований без нарушений | {len(self.reqs) - len(reqs_bad)} |")
        w(f"| Нарушений всего (подтверждённых) | {len(self.confirmed)} |")
        w(f"| — по отдельным требованиям | {sum(1 for x in self.confirmed if x.scope == 'requirement')} |")
        w(f"| — по набору в целом | {sum(1 for x in self.confirmed if x.scope == 'set')} |")
        w(f"| Критичных | {sev['critical']} |")
        w(f"| Существенных | {sev['major']} |")
        w(f"| Незначительных | {sev['minor']} |")
        w(f"| Отклонено при перепроверке / без подтверждённой цитаты | {len(self.discarded)} |")
        w("")
        by_crit = Counter(x.criterion for x in self.confirmed)
        if by_crit:
            w("Нарушения по критериям:\n")
            w("| Критерий | Пункт стандарта | Нарушений |\n| :--- | :--- | ---: |")
            for code, n in by_crit.most_common():
                w(f"| {C.name(code)} | {C.ref(code)} | {n} |")
            w("")
        w("### Критичные дефекты\n")
        for cls, codes in C.CRITICAL_CLASSES.items():
            items = [x for x in self.confirmed if x.criterion in codes]
            crit_items = [x for x in items if x.severity == "critical"]
            w(f"**{cls} формулировки** — всего {len(items)}, из них критичных {len(crit_items)}:\n")
            if not items:
                w("- не выявлено\n")
                continue
            for x in sorted(items, key=lambda z: (C.SEVERITY_ORDER[z.severity], z.iid)):
                w(f"- {self._issue_line(x)}")
            w("")
        known = set().union(*C.CRITICAL_CLASSES.values())
        other = [x for x in self.confirmed if x.severity == "critical" and x.criterion not in known]
        if other:
            w("**Прочие критичные дефекты:**\n")
            for x in other:
                w(f"- {self._issue_line(x)}")
            w("")

        # 6. итог
        verdict, why = self.verdict()
        w("## 6. Итог\n")
        w(f"**Можно ли начинать разработку и тестирование: {verdict}.**\n")
        w(why + "\n")
        summary = (self.verify_out or {}).get("summary")
        if summary:
            w(f"Резюме ревьюера: {summary}\n")
        w("### Что исправить в первую очередь\n")
        for n, (text, ids) in enumerate(self._priorities(), 1):
            ref = f" ({', '.join(ids)})" if ids else ""
            w(f"{n}. {text}{ref}")
        w("")

        # приложения
        w("## Приложение A. Отклонённые и неподтверждённые замечания\n")
        if not self.discarded:
            w("Нет.\n")
        else:
            w("Эти замечания модели не вошли в выводы: цитата не найдена в документе или замечание "
              "отклонено при перепроверке.\n")
            w("| ID | Требование | Критерий | Место | Замечание | Причина |")
            w("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for x in self.discarded:
                l = x.locations[0]
                where = self.doc.location_label(l.line_start, l.line_end) if l.line_start else "—"
                w(f"| {x.iid} | {_cell(', '.join(x.req_ids) or 'набор')} | {_cell(C.name(x.criterion))} | "
                  f"{_cell(where)} | {_cell(x.problem[:200])} | {_cell(x.status_reason)} |")
            w("")
        w("## Приложение B. Сигналы автоматического линтера\n")
        w("Детерминированные маркеры возможных дефектов (размытые слова, заглушки, незаполненные поля). "
          "Передавались модели как подсказки; нарушениями не считаются без подтверждения.\n")
        if self.lint_hits:
            w("| Строка | Правило | Фрагмент | Подсказка |\n| ---: | :--- | :--- | :--- |")
            for h in self.lint_hits:
                w(f"| {h.line} | {h.rule} | {_cell(_q(h.fragment, 60))} | {_cell(h.hint)} |")
        else:
            w("Нет срабатываний.")
        w("")
        w("## Приложение C. Методика\n")
        w("1. Документ читается и построчно нумеруется; для PDF сохраняется номер страницы.\n"
          "2. Требования выделяются моделью; пункты с явными идентификаторами дополнительно контролируются "
          "парсером, каждая цитата сверяется с текстом документа.\n"
          "3. Каждое требование проверяется по свойствам ISO/IEC/IEEE 29148 п. 5.2.5 и IEEE 830 п. 4.3.\n"
          "4. Набор проверяется целиком по 29148 п. 5.2.6 и IEEE 830 п. 4.3 (непротиворечивость, полнота, "
          "ранжирование, модифицируемость, прослеживаемость).\n"
          "5. Каждое замечание обязано содержать дословную цитату; агент находит её в документе и подставляет "
          "номер строки. Замечания без найденной цитаты в выводы не включаются.\n"
          "6. Отдельный проход перепроверки отсеивает ложные срабатывания и дубли и корректирует серьёзность.\n"
          "7. Итог определяется правилом: есть критичные дефекты → «нет»; есть существенные → «условно»; "
          "иначе → «да».\n")
        w("Серьёзность: **критично** — нельзя однозначно реализовать/протестировать или есть противоречие; "
          "**существенно** — высокий риск неверной реализации, пропущенный сценарий; **незначительно** — "
          "оформление, терминология.\n")
        return "\n".join(out).rstrip() + "\n"

    def _issue_md(self, x: Issue, with_reqs: bool = False) -> str:
        head = f"- **{x.iid}** · {C.name(x.criterion)} ({C.ref(x.criterion)}) · **{C.SEVERITIES[x.severity]}**"
        if with_reqs and x.req_ids:
            head += f" · связанные: {', '.join(x.req_ids)}"
        parts = [head]
        for l in x.locations:
            parts.append(f"  - Место: {self.doc.location_label(l.line_start, l.line_end)} — {_q(l.quote)}")
        parts.append(f"  - Проблема: {x.problem}")
        if x.fix:
            parts.append(f"  - Как исправить: {x.fix}")
        return "\n".join(parts) + "\n"

    def _issue_line(self, x: Issue) -> str:
        l = x.locations[0]
        lines = sorted({loc.line_start for loc in x.locations if loc.line_start})
        where = ("строки " + ", ".join(map(str, lines))) if len(lines) > 1 else self.doc.location_label(l.line_start, l.line_end)
        owner = ", ".join(x.req_ids) if x.req_ids else "набор"
        return (f"**{x.iid}** [{C.SEVERITIES[x.severity]}] {owner}, {where}, {_q(l.quote, 90)}: "
                f"{x.problem}")

    def _priorities(self) -> list[tuple[str, list[str]]]:
        ok_ids = {x.iid for x in self.confirmed}
        pr = []
        for p in (self.verify_out or {}).get("priorities", []):
            ids = [str(v) for v in (p.get("issues") or []) if str(v) in ok_ids]
            text = str(p.get("text") or "").strip()
            if text and ids:
                pr.append((text, ids))
        if pr:
            return pr[:7]
        # детерминированный запасной вариант: критичные, затем существенные
        ordered = sorted(self.confirmed, key=lambda z: (C.SEVERITY_ORDER[z.severity], z.scope != "set", z.iid))
        return [((x.fix or x.problem), [x.iid]) for x in ordered[:7]] or [("Исправлений не требуется.", [])]

    # ------------------------------------------------------------- outputs
    def to_json(self) -> dict:
        return {
            "run": asdict(self.info),
            "requirements": [r.to_dict() for r in self.reqs],
            "requirement_results": {
                rid: {"criteria": self.req_status(rid), "issues": [i.to_dict() for i in res.issues]}
                for rid, res in self.per_req.items()
            },
            "set_result": {
                "criteria": {c: {"status": self.set_status(c),
                                 "comment": (self.set_res.criteria.get(c).comment if self.set_res.criteria.get(c) else "")}
                             for c in C.SET_CODES},
                "issues": [i.to_dict() for i in self.set_res.issues],
            },
            "verdict": self.verdict()[0],
            "review": self.verify_out,
            "lint": [asdict(h) for h in self.lint_hits],
        }

    def write(self, path: Path) -> list[Path]:
        path.parent.mkdir(parents=True, exist_ok=True)
        md = self.markdown()
        written = []
        ext = path.suffix.lower()
        if ext in (".html", ".htm"):
            path.write_text(_to_html(md, self.doc.title), "utf-8")
        elif ext == ".json":
            path.write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=2), "utf-8")
        else:
            path.write_text(md, "utf-8")
        written.append(path)
        # машиночитаемая копия рядом — для повторной проверки/сравнения прогонов
        if ext != ".json":
            jp = path.with_suffix(".json")
            jp.write_text(json.dumps(self.to_json(), ensure_ascii=False, indent=2), "utf-8")
            written.append(jp)
        return written


def _to_html(md: str, title: str) -> str:
    try:
        import markdown  # type: ignore

        body = markdown.markdown(md, extensions=["tables"])
    except ImportError:
        import html

        body = f"<pre>{html.escape(md)}</pre>"
    return (f"<!DOCTYPE html><html lang=\"ru\"><head><meta charset=\"utf-8\"><title>Отчёт: {title}</title>"
            "<style>body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;"
            "line-height:1.5}table{border-collapse:collapse;font-size:.9em}td,th{border:1px solid #ccc;"
            "padding:4px 6px;vertical-align:top}blockquote{color:#444;border-left:3px solid #ccc;margin-left:0;"
            "padding-left:1em}</style></head><body>" + body + "</body></html>")
