"""Оркестрация прогона: документ → нарезка → проверки → перепроверка → отчёт."""
from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import __version__
from .analyze import IssueFactory, check_requirements, check_set, verify
from .config import ROOT
from .document import load_document
from .lint import lint
from .llm import LLMClient
from .models import RunInfo
from .report import Report
from .segment import segment


def agent_version() -> str:
    try:
        commit = subprocess.run(["git", "-C", str(ROOT), "describe", "--tags", "--always", "--dirty"],
                                capture_output=True, text=True, timeout=5)
        if commit.returncode == 0 and commit.stdout.strip():
            return f"{__version__} ({commit.stdout.strip()})"
    except (OSError, subprocess.SubprocessError):
        pass
    return f"{__version__} (без git)"


def _now() -> str:
    now = datetime.now().astimezone()
    z = now.strftime("%z")
    return now.strftime("%Y-%m-%d %H:%M:%S") + f" (UTC{z[:3]}:{z[3:]})"


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def run(input_path: Path, output_path: Path, llm: LLMClient, segment_mode: str = "llm",
        batch_size: int = 6, do_verify: bool = True) -> list[Path]:
    t0 = time.time()
    log(f"1/6 Чтение документа: {input_path}")
    doc = load_document(input_path)
    log(f"    формат {doc.fmt}, строк {len(doc.lines)}, заголовок «{doc.title}»")

    info = RunInfo(
        document_name=doc.name, document_title=doc.title, document_sha256=doc.sha256, started_at=_now(),
        provider=llm.cfg.provider, model=llm.cfg.model, agent_version=agent_version(),
    )

    log("2/6 Линтер формулировок")
    hits = lint(doc)
    info.lint_hits = len(hits)
    log(f"    сигналов: {len(hits)}")

    log("3/6 Нарезка требований")
    reqs, notes = segment(doc, llm, segment_mode)
    info.notes.extend(notes)
    log(f"    требований: {len(reqs)}")

    factory = IssueFactory(doc)
    log("4/6 Проверка каждого требования")
    per_req = check_requirements(doc, reqs, llm, hits, factory, batch_size=batch_size)

    log("5/6 Проверка набора требований")
    set_res = check_set(doc, reqs, per_req, llm, hits, factory)

    all_issues = [i for r in per_req.values() for i in r.issues] + set_res.issues
    verify_out: dict = {"summary": "", "priorities": []}
    if do_verify:
        log("    перепроверка замечаний")
        verify_out = verify(doc, all_issues, llm)
    else:
        info.notes.append("Перепроверка замечаний отключена (--no-verify).")

    ungrounded = sum(1 for i in all_issues if i.status == "ungrounded")
    if ungrounded:
        info.notes.append(f"{ungrounded} замечани(й/я) модели без подтверждённой цитаты исключены из выводов "
                          "(см. приложение A).")

    info.finished_at = _now()
    info.llm_calls = llm.calls
    info.cache_hits = llm.cache_hits
    if len(llm.models_used) > 1:
        info.model = " → ".join(llm.models_used)
        info.notes.append("Основная модель была недоступна, прогон переключался на запасные: "
                          + " → ".join(llm.models_used) + ".")
    log("6/6 Запись отчёта")
    rep = Report(doc, info, reqs, per_req, set_res, verify_out, hits)
    paths = rep.write(output_path)
    verdict = rep.verdict()[0]
    log(f"Готово за {time.time() - t0:.0f} с. Нарушений: {len(rep.confirmed)}. Итог: {verdict}")
    for p in paths:
        log(f"    {p}")
    return paths
