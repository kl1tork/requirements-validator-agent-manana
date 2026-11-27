"""Структуры данных, которые передаются между этапами пайплайна."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Requirement:
    rid: str                      # идентификатор в отчёте: R-01, R-02 ...
    doc_id: Optional[str]         # идентификатор в документе (Ф-1, п. 3 ...) или None
    section: str                  # раздел документа
    line_start: int               # 1-based, глобальная нумерация строк документа
    line_end: int
    quote: str                    # дословная цитата из документа
    summary: str                  # краткая формулировка
    kind: str = ""                # тип: функциональное, НФТ, API ...
    source: str = "llm"           # llm | rules (кто выделил)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Location:
    line_start: int
    line_end: int
    quote: str                    # фрагмент, найденный в документе дословно
    grounded: bool = True         # цитата подтверждена текстом документа
    match: str = "exact"          # exact | normalized | fuzzy | none

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Issue:
    iid: str                      # V-001 ...
    scope: str                    # requirement | set
    criterion: str                # код критерия из criteria.py
    severity: str                 # critical | major | minor
    problem: str
    fix: str
    locations: list[Location] = field(default_factory=list)
    req_ids: list[str] = field(default_factory=list)
    status: str = "confirmed"     # confirmed | rejected | ungrounded
    status_reason: str = ""
    duplicate_of: list[str] = field(default_factory=list)  # ID замечаний, которые дублирует отклонённое

    @property
    def grounded(self) -> bool:
        return bool(self.locations) and all(l.grounded for l in self.locations)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["locations"] = [l.to_dict() for l in self.locations]
        return d


@dataclass
class CriterionVerdict:
    code: str
    status: str                   # ok | violation | n/a
    comment: str = ""


@dataclass
class RequirementResult:
    rid: str
    criteria: dict[str, str] = field(default_factory=dict)   # code -> ok|violation|n/a
    issues: list[Issue] = field(default_factory=list)


@dataclass
class SetResult:
    criteria: dict[str, CriterionVerdict] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)


@dataclass
class RunInfo:
    document_name: str
    document_title: str
    document_sha256: str
    started_at: str
    finished_at: str = ""
    provider: str = ""
    model: str = ""
    agent_version: str = ""
    llm_calls: int = 0
    cache_hits: int = 0
    lint_hits: int = 0
    notes: list[str] = field(default_factory=list)
