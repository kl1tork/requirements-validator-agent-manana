"""HTML-версия отчёта в строгом «банковском» оформлении (без внешних зависимостей и CDN).

Страница самодостаточна: один файл, открывается двойным щелчком, работает офлайн,
поддерживает светлую и тёмную тему, фильтр замечаний по критичности и печать.
"""
from __future__ import annotations

import html
from collections import Counter
from typing import TYPE_CHECKING

from . import AGENT_NAME
from . import criteria as C

if TYPE_CHECKING:  # pragma: no cover
    from .models import Issue
    from .report import Report

SEV_CLASS = {"critical": "crit", "major": "major", "minor": "minor"}
MARK = {"violation": ("✖", "bad"), "ok": ("✔", "ok"), "n/a": ("—", "na"), "unconfirmed": ("?", "warn")}


def _e(s: object) -> str:
    return html.escape(str(s or ""), quote=True)


def _where(x: "Issue") -> str:
    lines = sorted({loc.line_start for loc in x.locations if loc.line_start})
    if not lines:
        return "весь документ"
    return ("строка " if len(lines) == 1 else "строки ") + ", ".join(map(str, lines))


def _issue(x: "Issue") -> str:
    quote = x.locations[0].quote if x.locations else ""
    owner = ", ".join(x.req_ids) if x.req_ids else "набор"
    return (
        f'<article class="issue sev-{SEV_CLASS[x.severity]}" data-sev="{x.severity}">'
        f'<header><span class="iid">{_e(x.iid)}</span>'
        f'<span class="badge {SEV_CLASS[x.severity]}">{_e(C.SEVERITIES[x.severity])}</span>'
        f'<span class="crit-name">{_e(C.name(x.criterion))}</span>'
        f'<span class="where">{_e(owner)} · {_e(_where(x))}</span></header>'
        + (f'<blockquote>«{_e(quote)}»</blockquote>' if quote else "")
        + f'<p><b>Проблема.</b> {_e(x.problem)}</p>'
        + (f'<p class="fix"><b>Как исправить.</b> {_e(x.fix)}</p>' if x.fix else "")
        + "</article>"
    )


def render(rep: "Report") -> str:
    i, doc = rep.info, rep.doc
    verdict, verdict_note = rep.verdict()
    tone = "bad" if verdict.startswith("НЕТ") else "warn" if verdict.startswith("УСЛОВНО") else "ok"
    sev = Counter(x.severity for x in rep.confirmed)
    with_issues = sum(1 for r in rep.reqs if rep.per_req.get(r.rid)
                      and any(x.status == "confirmed" for x in rep.per_req[r.rid].issues))
    summary = (rep.verify_out or {}).get("summary", "")

    kpis = [
        ("Требований", len(rep.reqs), ""),
        ("С нарушениями", with_issues, ""),
        ("Нарушений", len(rep.confirmed), ""),
        ("Критичных", sev["critical"], "crit"),
        ("Существенных", sev["major"], "major"),
        ("Незначительных", sev["minor"], "minor"),
    ]
    kpi_html = "".join(f'<div class="kpi {c}"><span>{_e(n)}</span><b>{v}</b></div>' for n, v, c in kpis)

    prio = "".join(
        f'<li>{_e(text)} <span class="refs">{_e(", ".join(ids))}</span></li>' for text, ids in rep._priorities()
    )

    set_rows = []
    for code in C.SET_CODES:
        st = rep.set_status(code)
        sym, cls = MARK[st]
        refs = rep.set_dup_refs(code)
        n = sum(1 for x in rep.set_res.issues if x.criterion == code and x.status == "confirmed")
        label = sym + (f" {n}" if n else "") + (" · " + ", ".join(refs) if refs else "")
        cv = rep.set_res.criteria.get(code)
        set_rows.append(f'<tr><td>{_e(C.name(code))}<small>{_e(C.ref(code))}</small></td>'
                        f'<td><span class="mark {cls}">{_e(label)}</span></td><td>{_e(cv.comment if cv else "")}</td></tr>')

    set_issues = [x for x in rep.set_res.issues if x.status == "confirmed"]
    req_blocks = []
    for r in rep.reqs:
        res = rep.per_req.get(r.rid)
        issues = sorted([x for x in (res.issues if res else []) if x.status == "confirmed"],
                        key=lambda z: (C.SEVERITY_ORDER[z.severity], z.iid))
        worst = issues[0].severity if issues else ""
        status = (f'<span class="badge {SEV_CLASS[worst]}">{len(issues)}</span>' if issues
                  else '<span class="badge clean">без замечаний</span>')
        sevs = " ".join(sorted({x.severity for x in issues}))
        req_blocks.append(
            f'<details class="req" data-sevs="{sevs}"{" open" if worst == "critical" else ""}>'
            f'<summary><span class="rid">{_e(r.rid)}</span>'
            f'<span class="docid">{_e(r.doc_id or "—")}</span>'
            f'<span class="rsum">{_e(r.summary)}</span>'
            f'<span class="rloc">строка {_e(r.line_start)}</span>{status}</summary>'
            f'<blockquote>«{_e(r.quote)}»</blockquote>'
            + "".join(_issue(x) for x in issues) + "</details>"
        )

    passport = [
        ("Документ", f"{i.document_title} ({i.document_name})"),
        ("Дата прогона", i.started_at),
        ("Модель", f"{i.model} · {i.provider}, temperature 0"),
        ("Версия агента", i.agent_version),
        ("Обращений к модели", f"{i.llm_calls} (+ {i.cache_hits} из кэша)"),
        ("SHA-256", i.document_sha256[:16] + "…"),
    ]
    pass_html = "".join(f"<div><dt>{_e(k)}</dt><dd>{_e(v)}</dd></div>" for k, v in passport)

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(AGENT_NAME)} — отчёт: {_e(doc.title)}</title>
<style>{CSS}</style></head>
<body>
<header class="top"><div class="wrap">
  <div class="brand"><span class="logo" aria-hidden="true">M</span>
    <div><b>{_e(AGENT_NAME)}</b><span>агент проверки требований</span></div></div>
  <div class="std">ISO/IEC/IEEE 29148:2018 · IEEE 830-1998</div>
</div></header>
<main class="wrap">
  <section class="hero">
    <p class="eyebrow">Отчёт о проверке требований</p>
    <h1>{_e(doc.title)}</h1>
    <div class="verdict {tone}"><div class="vicon" aria-hidden="true">{"!" if tone == "bad" else "✓" if tone == "ok" else "~"}</div>
      <div><b>{_e(verdict)}</b><p>{_e(verdict_note)}</p></div></div>
    <div class="kpis">{kpi_html}</div>
  </section>

  <section class="card"><h2>Что исправить в первую очередь</h2><ol class="prio">{prio}</ol>
    {f'<p class="note">{_e(summary)}</p>' if summary else ''}</section>

  <section class="card"><h2>Проверка всего набора требований</h2>
    <table class="set"><thead><tr><th>Свойство</th><th>Итог</th><th>Комментарий</th></tr></thead>
    <tbody>{''.join(set_rows)}</tbody></table>
    {''.join(_issue(x) for x in sorted(set_issues, key=lambda z: (C.SEVERITY_ORDER[z.severity], z.iid)))}
  </section>

  <section class="card"><div class="head-row"><h2>Требования и замечания</h2>
    <div class="filter" role="group" aria-label="Фильтр по критичности">
      <button class="on" data-f="all">Все</button><button data-f="critical">Критичные</button>
      <button data-f="major">Существенные</button><button data-f="minor">Незначительные</button></div></div>
    {''.join(req_blocks)}
  </section>

  <section class="card"><h2>Паспорт прогона</h2><dl class="passport">{pass_html}</dl></section>
  <footer>Отчёт сформирован агентом «{_e(AGENT_NAME)}» автоматически. Каждое замечание подтверждено цитатой из документа;
  номера строк — по входному файлу. Подробная версия — в report.md.</footer>
</main>
<script>{JS}</script>
</body></html>
"""


CSS = """
:root{--navy:#0a6b45;--navy2:#0a6b45;--green:#c9a227;--gold:#c9a227;--bg:#f6f7f4;--card:#fff;--text:#14231c;--muted:#5d6b63;
--line:#e3e8e3;--crit:#c62828;--crit-bg:#fdecec;--major:#b26a00;--major-bg:#fff4e0;--minor:#3d6aa8;--minor-bg:#e9f0fb;
--ok:#0f8a5f;--ok-bg:#e6f5ee}
@media (prefers-color-scheme:dark){:root{--bg:#0d1612;--card:#15211b;--text:#e8efe9;--muted:#9fb2a6;--line:#24362c;
--crit:#ff8a80;--crit-bg:#3a1c1c;--major:#ffc061;--major-bg:#3a2c12;--minor:#8fb6ee;--minor-bg:#18283d;--ok:#5fd3a2;--ok-bg:#123227}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
.top{background:var(--navy);color:#fff;border-bottom:3px solid var(--gold)}.top .wrap{display:flex;justify-content:space-between;align-items:center;height:64px}
.brand{display:flex;gap:12px;align-items:center}.brand b{display:block;font-size:18px;letter-spacing:.3px}
.brand span{font-size:12px;opacity:.75}.std{font-size:12px;opacity:.7}
.logo{width:38px;height:38px;border-radius:10px;background:var(--green);display:grid;place-items:center;font-weight:700;font-size:20px}
.hero{padding:28px 0 8px}.eyebrow{margin:0;color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.8px}
h1{margin:4px 0 18px;font-size:28px;line-height:1.2}h2{margin:0 0 14px;font-size:18px}
.verdict{display:flex;gap:16px;align-items:flex-start;border-radius:14px;padding:18px 20px;border:1px solid}
.verdict p{margin:4px 0 0;color:var(--muted)}.verdict b{font-size:17px}
.verdict.bad{background:var(--crit-bg);border-color:var(--crit)}.verdict.warn{background:var(--major-bg);border-color:var(--major)}
.verdict.ok{background:var(--ok-bg);border-color:var(--ok)}
.vicon{flex:none;width:36px;height:36px;border-radius:50%;display:grid;place-items:center;font-weight:700;color:#fff;background:var(--crit)}
.verdict.warn .vicon{background:var(--major)}.verdict.ok .vicon{background:var(--ok)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:18px 0 8px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi span{display:block;font-size:12px;color:var(--muted)}.kpi b{font-size:26px}
.kpi.crit b{color:var(--crit)}.kpi.major b{color:var(--major)}.kpi.minor b{color:var(--minor)}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px 24px;margin:18px 0}
.prio{margin:0;padding-left:22px}.prio li{margin:8px 0}.refs{color:var(--muted);font-size:12px;white-space:nowrap}
.note{color:var(--muted);border-top:1px solid var(--line);padding-top:12px;margin:16px 0 0}
table.set{width:100%;border-collapse:collapse;font-size:14px;margin-bottom:8px}
.set th{text-align:left;color:var(--muted);font-weight:500;font-size:12px;border-bottom:1px solid var(--line);padding:8px}
.set td{border-bottom:1px solid var(--line);padding:10px 8px;vertical-align:top}.set td small{display:block;color:var(--muted);font-size:11px}
.mark{display:inline-block;border-radius:6px;padding:2px 8px;font-size:13px;white-space:nowrap}
.mark.bad{background:var(--crit-bg);color:var(--crit)}.mark.ok{background:var(--ok-bg);color:var(--ok)}
.mark.warn{background:var(--major-bg);color:var(--major)}.mark.na{color:var(--muted)}
.head-row{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:6px}
.head-row h2{margin:0}.filter button{border:1px solid var(--line);background:transparent;color:var(--text);border-radius:999px;
padding:5px 12px;font-size:13px;cursor:pointer;margin-left:4px}.filter button.on{background:var(--navy);color:#fff;border-color:var(--navy)}
details.req{border:1px solid var(--line);border-radius:12px;margin:10px 0;overflow:hidden}
details.req summary{display:grid;grid-template-columns:52px 90px minmax(0,1fr) auto auto;gap:10px;align-items:center;padding:12px 14px;cursor:pointer;list-style:none}
details.req summary::-webkit-details-marker{display:none}details.req[open] summary{border-bottom:1px solid var(--line)}
.rid{font-weight:600;color:var(--navy2)}@media (prefers-color-scheme:dark){.rid{color:#e0c35a}}
.logo{color:#0a3d28}.eyebrow{color:var(--gold)!important;font-weight:600}h2{border-left:4px solid var(--gold);padding-left:10px}
.docid,.rloc{color:var(--muted);font-size:13px}.rsum{font-size:14px}
details.req>blockquote{margin:12px 14px;color:var(--muted);font-size:13px}
blockquote{border-left:3px solid var(--line);margin:8px 0;padding:2px 0 2px 12px;color:var(--muted)}
.badge{border-radius:999px;padding:2px 10px;font-size:12px;font-weight:600;white-space:nowrap}
.badge.crit{background:var(--crit-bg);color:var(--crit)}.badge.major{background:var(--major-bg);color:var(--major)}
.badge.minor{background:var(--minor-bg);color:var(--minor)}.badge.clean{background:var(--ok-bg);color:var(--ok)}
.issue{border-left:4px solid var(--line);margin:12px 14px;padding:4px 0 4px 14px}
.issue.sev-crit{border-color:var(--crit)}.issue.sev-major{border-color:var(--major)}.issue.sev-minor{border-color:var(--minor)}
.issue header{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px}.iid{font-weight:700}
.crit-name{font-weight:600}.where{color:var(--muted)}.issue p{margin:6px 0;font-size:14px}.fix{color:var(--ok)}
.card>.issue{margin:12px 0}
.passport{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px 24px;margin:0}
.passport dt{font-size:12px;color:var(--muted)}.passport dd{margin:2px 0 0;font-size:14px;word-break:break-word}
footer{color:var(--muted);font-size:12px;padding:8px 0 40px}
.hidden{display:none}
.brand span{white-space:nowrap}
@media (max-width:640px){details.req summary{grid-template-columns:44px minmax(0,1fr) auto;padding:10px}.docid,.rloc{display:none}
h1{font-size:22px}.std{display:none}.verdict b{font-size:15px}.wrap{padding:0 12px}.card{padding:16px 14px}
.issue{margin:10px}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}table.set td:nth-child(3){font-size:12px}}
body{overflow-x:hidden}
@media print{.filter{display:none}details.req{break-inside:avoid}.top{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
"""

JS = """
document.querySelectorAll('.filter button').forEach(b=>b.addEventListener('click',()=>{
 document.querySelectorAll('.filter button').forEach(x=>x.classList.toggle('on',x===b));
 const f=b.dataset.f;
 document.querySelectorAll('details.req').forEach(d=>{
  const has=f==='all'||(d.dataset.sevs||'').split(' ').includes(f);
  d.classList.toggle('hidden',!has); if(f!=='all'&&has) d.open=true;
  d.querySelectorAll('.issue').forEach(i=>i.classList.toggle('hidden',f!=='all'&&i.dataset.sev!==f));
 });
}));
"""
