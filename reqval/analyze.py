"""Проверка требований: каждое по отдельности, набор целиком, перепроверка замечаний."""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from . import criteria as C
from . import prompts
from .document import Document
from .grounding import Grounder
from .jsonutil import as_int, as_list
from .lint import LintHit, format_hints, hints_for_lines
from .llm import LLMClient
from .models import CriterionVerdict, Issue, Location, Requirement, RequirementResult, SetResult

_SEV = {"critical", "major", "minor"}


class IssueFactory:
    def __init__(self, doc: Document):
        self.doc = doc
        self.grounder = Grounder(doc)
        self.n = 0

    def make(self, scope: str, raw: dict, req_ids: list[str], locs_raw: list[dict],
             default_line: Optional[int] = None) -> Optional[Issue]:
        crit = str(raw.get("criterion") or "").strip()
        if crit not in C.ALL:
            crit = _guess_criterion(crit, scope)
        sev = str(raw.get("severity") or "major").lower().strip()
        sev = sev if sev in _SEV else "major"
        problem = str(raw.get("problem") or "").strip()
        if not problem:
            return None
        locations: list[Location] = []
        for lr in locs_raw:
            hint = as_int(lr.get("line"), 0) or default_line
            loc = self.grounder.locate(str(lr.get("quote") or ""), hint)
            locations.append(loc)
        if not locations:
            locations.append(self.grounder.locate("", default_line))
        self.n += 1
        issue = Issue(
            iid=f"V-{self.n:03d}", scope=scope, criterion=crit, severity=sev, problem=problem,
            fix=str(raw.get("fix") or "").strip(), locations=locations, req_ids=req_ids,
        )
        if not issue.grounded:
            issue.status = "ungrounded"
            issue.status_reason = "Цитата не найдена в тексте документа — замечание не подтверждено."
        return issue


# ------------------------------------------------------------- per requirement
def check_requirements(doc: Document, reqs: list[Requirement], llm: LLMClient, lint_hits: list[LintHit],
                       factory: IssueFactory, batch_size: int = 6) -> dict[str, RequirementResult]:
    results: dict[str, RequirementResult] = {r.rid: RequirementResult(r.rid) for r in reqs}
    by_id = {r.rid: r for r in reqs}
    numbered = doc.numbered()
    batches = [reqs[i:i + batch_size] for i in range(0, len(reqs), batch_size)]
    for bi, batch in enumerate(batches, 1):
        payload = [{"id": r.rid, "doc_id": r.doc_id, "section": r.section, "lines": f"{r.line_start}-{r.line_end}",
                    "quote": r.quote} for r in batch]
        hits: list[LintHit] = []
        for r in batch:
            hits += hints_for_lines(lint_hits, r.line_start, r.line_end)
        data = llm.complete_json(prompts.SYSTEM, prompts.requirement_prompt(numbered, payload, format_hints(hits)),
                                 stage=f"требования {bi}/{len(batches)}")
        items = as_list(data.get("results") if isinstance(data, dict) else data)
        for item in items:
            if not isinstance(item, dict):
                continue
            rid = _norm_rid(item.get("id"), by_id)
            if not rid:
                continue
            req = by_id[rid]
            res = results[rid]
            crit = item.get("criteria") or {}
            if isinstance(crit, dict):
                for code in C.INDIVIDUAL_CODES:
                    v = str(crit.get(code, "n/a")).lower()
                    res.criteria[code] = v if v in ("ok", "violation", "n/a") else "n/a"
            for raw in as_list(item.get("issues")):
                if not isinstance(raw, dict):
                    continue
                issue = factory.make("requirement", raw, [rid], [raw], default_line=req.line_start)
                if issue:
                    res.issues.append(issue)
                    res.criteria[issue.criterion] = "violation"
    return results


# ---------------------------------------------------------------------- set
def check_set(doc: Document, reqs: list[Requirement], per_req: dict[str, RequirementResult], llm: LLMClient,
              lint_hits: list[LintHit], factory: IssueFactory) -> SetResult:
    table = "\n".join(f"{r.rid} | {r.doc_id or '—'} | {r.line_start}-{r.line_end} | {r.summary}" for r in reqs)
    digest_lines = []
    for rid, res in per_req.items():
        for i in res.issues:
            l = i.locations[0]
            digest_lines.append(f"- {rid} L{l.line_start} [{i.criterion}/{i.severity}] {i.problem[:160]}")
    digest = "\n".join(digest_lines) or "(нет)"
    set_hints = [h for h in lint_hits if h.rule in ("placeholder", "to_be_filled", "empty_value", "unfilled_choice")]
    data = llm.complete_json(
        prompts.SYSTEM, prompts.set_prompt(doc.numbered(), table, digest, format_hints(set_hints[:60])),
        stage="набор требований",
    )
    result = SetResult()
    crit = data.get("criteria", {}) if isinstance(data, dict) else {}
    for code in C.SET_CODES:
        v = crit.get(code) if isinstance(crit, dict) else None
        if isinstance(v, dict):
            st = str(v.get("status", "n/a")).lower()
            result.criteria[code] = CriterionVerdict(code, st if st in ("ok", "violation") else "n/a",
                                                     str(v.get("comment") or ""))
        elif isinstance(v, str):
            result.criteria[code] = CriterionVerdict(code, v if v in ("ok", "violation") else "n/a")
        else:
            result.criteria[code] = CriterionVerdict(code, "n/a")
    valid = {r.rid for r in reqs}
    for raw in as_list(data.get("issues") if isinstance(data, dict) else []):
        if not isinstance(raw, dict):
            continue
        related = [x for x in (str(v) for v in as_list(raw.get("related"))) if x in valid]
        locs = [l for l in as_list(raw.get("locations")) if isinstance(l, dict)] or [raw]
        issue = factory.make("set", raw, related, locs)
        if issue:
            result.issues.append(issue)
            cv = result.criteria.get(issue.criterion)
            if cv is None:
                result.criteria[issue.criterion] = CriterionVerdict(issue.criterion, "violation")
            else:
                cv.status = "violation"
    return result


# ----------------------------------------------------------------- verify
def verify(doc: Document, issues: list[Issue], llm: LLMClient) -> dict[str, Any]:
    """Перепроверка: отсеивает ложные срабатывания и дубли, даёт резюме и приоритеты."""
    active = [i for i in issues if i.status == "confirmed"]
    if not active:
        return {"summary": "", "priorities": []}
    lines = []
    for i in active:
        locs = "; ".join(f"L{l.line_start} «{l.quote[:120]}»" for l in i.locations)
        lines.append(json.dumps({"id": i.iid, "scope": i.scope, "req": i.req_ids, "criterion": i.criterion,
                                 "severity": i.severity, "where": locs, "problem": i.problem, "fix": i.fix},
                                ensure_ascii=False))
    data = llm.complete_json(prompts.SYSTEM, prompts.verify_prompt(doc.numbered(), "\n".join(lines)),
                             stage="перепроверка")
    by_id = {i.iid: i for i in active}
    for v in as_list(data.get("verdicts") if isinstance(data, dict) else []):
        if not isinstance(v, dict):
            continue
        issue = by_id.get(str(v.get("id")))
        if not issue:
            continue
        decision = str(v.get("decision", "confirm")).lower()
        if decision == "reject":
            issue.status = "rejected"
            dup = v.get("duplicate_of")
            issue.duplicate_of = [d for d in re.findall(r"V-\d+", str(dup or "")) if d != issue.iid]
            reason = str(v.get("reason") or "").strip()
            issue.status_reason = (f"Дубликат {dup}. " if dup else "") + reason
        else:
            sev = str(v.get("severity") or issue.severity).lower()
            if sev in _SEV and sev != issue.severity:
                issue.status_reason = f"Серьёзность скорректирована при перепроверке: {issue.severity} → {sev}."
                issue.severity = sev
    return {
        "summary": str(data.get("summary") or "") if isinstance(data, dict) else "",
        "priorities": [p for p in as_list(data.get("priorities") if isinstance(data, dict) else [])
                       if isinstance(p, dict)],
    }


# ---------------------------------------------------------------- helpers
def _norm_rid(v: Any, by_id: dict) -> Optional[str]:
    s = str(v or "").strip()
    if s in by_id:
        return s
    n = as_int(s, -1)
    for rid in by_id:
        if as_int(rid, -2) == n:
            return rid
    return None


def _guess_criterion(text: str, scope: str) -> str:
    t = text.lower()
    table = [
        ("однознач", "unambiguous"), ("ambig", "unambiguous"), ("провер", "verifiable"), ("verif", "verifiable"),
        ("полн", "complete" if scope == "requirement" else "set_complete"),
        ("complete", "complete" if scope == "requirement" else "set_complete"),
        ("противореч", "set_consistent" if scope == "set" else "correct"), ("consist", "set_consistent"),
        ("коррект", "correct"), ("correct", "correct"), ("атомар", "singular"), ("singular", "singular"),
        ("уместн", "appropriate"), ("design", "appropriate"), ("проектн", "appropriate"),
        ("необход", "necessary"), ("выполн", "feasible"), ("feasib", "feasible"),
        ("шаблон", "conforming"), ("conform", "conforming"), ("трассир", "traceable"), ("traceab", "traceable"),
        ("прослежив", "traceable" if scope == "requirement" else "set_traceable"),
        ("ранж", "ranked"), ("приорит", "ranked"), ("модифиц", "modifiable"), ("верси", "modifiable"),
        ("понятн", "set_comprehensible"), ("термин", "set_comprehensible"), ("валидац", "set_validatable"),
    ]
    for key, code in table:
        if key in t:
            return code
    return "correct" if scope == "requirement" else "set_complete"
