"""Локальное веб-приложение Manana: загрузить документ → посмотреть ход проверки → открыть и скачать отчёт.

Запуск:  python -m reqval.web        (откроется http://127.0.0.1:8765)
Только стандартная библиотека; сервер слушает лишь localhost, ключ LLM берётся из .env как у CLI.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import threading
import uuid
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from . import AGENT_NAME, __version__
from .brand import FAVICON, logo
from .config import ROOT, build_llm_config, load_env
from .document import SUPPORTED
from .llm import LLMClient, LLMError

RUNS = ROOT / "web_runs"
PORT = 8765
MAX_UPLOAD = 20 * 1024 * 1024
OUTPUTS = {"report.html": "text/html; charset=utf-8", "report.md": "text/markdown; charset=utf-8",
           "report.json": "application/json; charset=utf-8"}

_jobs: dict[str, dict] = {}
_lock = threading.Lock()  # пайплайн пишет прогресс в stderr — прогоны выполняем по одному


class _LogTee(io.TextIOBase):
    def __init__(self, job: dict, echo):
        self.job, self.echo, self.buf = job, echo, ""

    def write(self, s: str) -> int:
        self.echo.write(s)
        self.buf += s
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            if line.strip():
                self.job["log"].append(line.rstrip())
        return len(s)


def _run_job(job_id: str, src: Path, use_cache: bool) -> None:
    job = _jobs[job_id]
    with _lock:
        job["state"] = "running"
        try:
            cfg = build_llm_config(no_cache=not use_cache)
            llm = LLMClient(cfg, verbose=True)
            from .pipeline import run

            with contextlib.redirect_stderr(_LogTee(job, sys.__stderr__)):
                run(src, src.parent / "report.md", llm)
            job["state"] = "done"
        except (LLMError, ValueError, FileNotFoundError) as e:
            job["state"], job["error"] = "error", str(e)
        except Exception as e:  # noqa: BLE001 — показать пользователю, а не уронить сервер
            job["state"], job["error"] = "error", f"{type(e).__name__}: {e}"


class Handler(BaseHTTPRequestHandler):
    server_version = f"Manana/{__version__}"

    def log_message(self, fmt, *args):  # тише в консоли
        pass

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj: dict, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE.replace("{{NAME}}", AGENT_NAME).replace("{{VER}}", __version__)
                              .replace("{{EXT}}", ", ".join(sorted(SUPPORTED)))
                              .replace("{{LOGO}}", logo(32)).replace("{{FAVICON}}", FAVICON).encode(), "text/html; charset=utf-8")
        m = re.fullmatch(r"/status/([0-9a-f]{32})", self.path)
        if m:
            job = _jobs.get(m.group(1))
            if not job:
                return self._json({"error": "не найдено"}, 404)
            return self._json({k: job[k] for k in ("state", "log", "error", "name")})
        m = re.fullmatch(r"/runs/([0-9a-f]{32})/(report\.(?:html|md|json))(\?dl=1)?", self.path)
        if m and m.group(1) in _jobs:
            f = RUNS / m.group(1) / m.group(2)
            if f.exists():
                extra = {"Content-Disposition": f'attachment; filename="{m.group(2)}"'} if m.group(3) else None
                return self._send(200, f.read_bytes(), OUTPUTS[m.group(2)], extra)
        self._send(404, "Не найдено".encode(), "text/plain; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?")[0] != "/run":
            return self._send(404, b"", "text/plain")
        name = Path(unquote(self.headers.get("X-Filename", "document.txt"))).name
        ext = Path(name).suffix.lower()
        size = int(self.headers.get("Content-Length") or 0)
        if ext not in SUPPORTED:
            return self._json({"error": f"Формат {ext or '?'} не поддерживается. Нужен один из: "
                                        + ", ".join(sorted(SUPPORTED))}, 400)
        if not 0 < size <= MAX_UPLOAD:
            return self._json({"error": "Файл пустой или больше 20 МБ."}, 400)
        if _lock.locked():
            return self._json({"error": "Сейчас уже идёт проверка другого документа. Дождитесь её окончания."}, 409)
        job_id = uuid.uuid4().hex
        folder = RUNS / job_id
        folder.mkdir(parents=True)
        src = folder / (re.sub(r"[^\w.\- ]", "_", name).lstrip(".") or f"document{ext}")
        src.write_bytes(self.rfile.read(size))
        _jobs[job_id] = {"state": "queued", "log": [], "error": "", "name": name}
        use_cache = "nocache" not in self.path
        threading.Thread(target=_run_job, args=(job_id, src, use_cache), daemon=True).start()
        self._json({"id": job_id})


def main() -> int:
    load_env()
    try:
        LLMClient(build_llm_config(), verbose=False)
    except (LLMError, ValueError) as e:
        print(f"Ошибка конфигурации: {e}", file=sys.stderr)
        return 2
    RUNS.mkdir(exist_ok=True)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"{AGENT_NAME} запущена: {url}\nЧтобы остановить — закройте это окно или нажмите Ctrl+C.", flush=True)
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


PAGE = r"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{{NAME}} — проверка требований</title><link rel="icon" href="{{FAVICON}}">
<style>
:root{--green:#0a6b45;--gold:#c9a227;--bg:#f6f7f4;--card:#fff;--text:#14231c;--muted:#5d6b63;--line:#e3e8e3;--bad:#c62828;--badbg:#fdecec}
@media (prefers-color-scheme:dark){:root{--bg:#0d1612;--card:#15211b;--text:#e8efe9;--muted:#9fb2a6;--line:#24362c;--bad:#ff8a80;--badbg:#3a1c1c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
.top{background:var(--green);color:#fff;border-bottom:3px solid var(--gold)}.wrap{max-width:860px;margin:0 auto;padding:0 20px}
.top .wrap{display:flex;align-items:center;gap:12px;min-height:64px;padding-top:8px;padding-bottom:8px}.logo{width:42px;height:42px;border-radius:12px;background:#fff;
color:#0a3d28;display:grid;place-items:center;font-weight:700;font-size:20px}.top b{font-size:18px;display:block}.top span{font-size:12px;opacity:.8}
h1{font-size:26px;margin:28px 0 6px}.lead{color:var(--muted);margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:22px 24px;margin:16px 0}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:0;padding:0;list-style:none}
.steps li{border:1px solid var(--line);border-radius:12px;padding:12px 14px;font-size:14px}.steps b{color:var(--gold);display:block;font-size:13px}
.drop{border:2px dashed var(--line);border-radius:14px;padding:28px;text-align:center;cursor:pointer;transition:.15s}
.drop:hover,.drop.over{border-color:var(--green);background:rgba(10,107,69,.05)}.drop b{display:block;font-size:16px}.drop small{color:var(--muted)}
#file{display:none}.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-top:16px}
button.main{background:var(--green);color:#fff;border:0;border-radius:10px;padding:12px 22px;font-size:15px;font-weight:600;cursor:pointer}
button.main:disabled{opacity:.5;cursor:default}label.opt{font-size:13px;color:var(--muted)}
.err{color:var(--bad);background:var(--badbg);border-radius:10px;padding:10px 14px;margin-top:14px;display:none}
.bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden;margin:6px 0 14px}.bar i{display:block;height:8px;width:0;background:var(--gold);transition:width .4s}
.stage{font-weight:600}.log{font:12px/1.5 ui-monospace,Menlo,monospace;background:var(--bg);border-radius:10px;padding:10px 12px;max-height:180px;overflow:auto;color:var(--muted);white-space:pre-wrap}
.done a{display:inline-block;margin:6px 8px 0 0;border:1px solid var(--line);border-radius:10px;padding:8px 14px;color:var(--text);text-decoration:none;font-size:14px}
.done a.open{background:var(--green);color:#fff;border-color:var(--green);font-weight:600}
iframe{width:100%;height:78vh;border:1px solid var(--line);border-radius:14px;margin-top:14px;background:#fff}
.hidden{display:none}footer{color:var(--muted);font-size:12px;padding:10px 0 40px}
</style></head><body>
<header class="top"><div class="wrap"><span class="logo">{{LOGO}}</span><div><b>{{NAME}}</b><span>агент проверки требований · v{{VER}}</span></div></div></header>
<main class="wrap">
<h1>Проверка документа требований</h1>
<p class="lead">Загрузите документ — {{NAME}} разберёт его на требования, проверит по ISO/IEC/IEEE 29148 и IEEE 830 и покажет, что исправить до начала разработки.</p>
<section class="card"><ol class="steps">
<li><b>1. Загрузка</b>Выберите файл с требованиями</li><li><b>2. Проверка</b>Агент читает и анализирует, 1–5 минут</li>
<li><b>3. Отчёт</b>Вердикт, ошибки с цитатами, что исправить</li></ol></section>
<section class="card" id="up">
<div class="drop" id="drop"><b>Перетащите документ сюда или нажмите, чтобы выбрать</b><small>Форматы: {{EXT}}</small><div id="fname"></div></div>
<input type="file" id="file">
<div class="row"><button class="main" id="go" disabled>Проверить документ</button>
<label class="opt"><input type="checkbox" id="fresh"> Не брать ответы из кэша (заново спросить модель)</label></div>
<div class="err" id="err"></div></section>
<section class="card hidden" id="prog"><div class="stage" id="stage">Подготовка…</div><div class="bar"><i id="bar"></i></div><div class="log" id="log"></div></section>
<section class="card hidden done" id="done"><div class="stage">Готово — отчёт ниже</div>
<a class="open" id="aopen" target="_blank">Открыть отчёт в новой вкладке</a><a id="ahtml">Скачать отчёт (.html)</a><a id="amd">Скачать отчёт (.md)</a><a id="ajson">Скачать данные (.json)</a>
<iframe id="frame" title="Отчёт"></iframe></section>
<footer>{{NAME}} работает на вашем компьютере; документ отправляется только в выбранную языковую модель (по умолчанию Gemini).</footer>
</main>
<script>
const $=id=>document.getElementById(id);let file=null;
const pick=f=>{file=f;$('fname').textContent=f?'Выбран: '+f.name:'';$('go').disabled=!f;$('err').style.display='none'};
$('drop').onclick=()=>$('file').click();$('file').onchange=e=>pick(e.target.files[0]);
['dragover','dragenter'].forEach(t=>$('drop').addEventListener(t,e=>{e.preventDefault();$('drop').classList.add('over')}));
['dragleave','drop'].forEach(t=>$('drop').addEventListener(t,e=>{e.preventDefault();$('drop').classList.remove('over')}));
$('drop').addEventListener('drop',e=>{if(e.dataTransfer.files[0])pick(e.dataTransfer.files[0])});
const err=m=>{$('err').textContent=m;$('err').style.display='block';$('go').disabled=!file};
$('go').onclick=async()=>{
 if(!file)return err('Сначала выберите файл.');
 $('go').disabled=true;$('done').classList.add('hidden');$('prog').classList.remove('hidden');$('log').textContent='';$('bar').style.width='3%';
 let r;try{r=await fetch('/run'+($('fresh').checked?'?nocache':''),{method:'POST',headers:{'X-Filename':encodeURIComponent(file.name)},body:file});}
 catch(e){$('prog').classList.add('hidden');return err('Не удалось связаться с приложением. Оно запущено?')}
 const j=await r.json();if(!r.ok){$('prog').classList.add('hidden');return err(j.error||'Ошибка')}
 poll(j.id)};
async function poll(id){
 const s=await (await fetch('/status/'+id)).json();
 $('log').textContent=s.log.join('\n');$('log').scrollTop=1e9;
 const st=[...s.log].reverse().find(l=>/^\d\/6/.test(l));
 if(st){$('stage').textContent=st.replace(/^(\d)\/6/,'Шаг $1 из 6 —');$('bar').style.width=(+st[0]/6*100)+'%'}
 if(s.state==='done'){$('prog').classList.add('hidden');const b='/runs/'+id+'/';
  $('aopen').href=b+'report.html';$('ahtml').href=b+'report.html?dl=1';$('amd').href=b+'report.md?dl=1';$('ajson').href=b+'report.json?dl=1';
  $('frame').src=b+'report.html';$('done').classList.remove('hidden');$('go').disabled=false;$('done').scrollIntoView({behavior:'smooth'});return}
 if(s.state==='error'){$('prog').classList.add('hidden');return err('Проверка остановилась: '+s.error)}
 setTimeout(()=>poll(id),1200)}
</script></body></html>"""


if __name__ == "__main__":
    sys.exit(main())
