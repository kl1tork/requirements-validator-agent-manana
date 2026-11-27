"""Локальное веб-приложение Manana: загрузить документ → посмотреть ход проверки → открыть и скачать отчёт.

Запуск:  python -m reqval.web        (откроется http://127.0.0.1:8765)

Переменные окружения:
  MANANA_HOST      адрес, на котором слушать (по умолчанию 127.0.0.1; 0.0.0.0 — доступ с телефона по Wi-Fi и в облаке)
  PORT             порт (по умолчанию 8765; облачные хостинги задают его сами)
  MANANA_PASSWORD  пароль на вход; обязательно задайте, если открываете приложение в сеть
Только стандартная библиотека; сервер слушает лишь localhost, ключ LLM берётся из .env как у CLI.
"""
from __future__ import annotations

import contextlib
import hashlib
import hmac
import os
import socket
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
from urllib.parse import parse_qs, unquote

from . import AGENT_NAME, __version__
from .brand import FAVICON, logo
from .criteria import INDIVIDUAL, SET
from .config import ROOT, build_llm_config, load_env
from .document import SUPPORTED
from .llm import LLMClient, LLMError
from .web_page import LOGIN_PAGE, MANIFEST, PAGE, SERVICE_WORKER

RUNS = ROOT / "web_runs"
PORT = 8765
ICONS = ROOT / "assets" / "icons"
PUBLIC = {"/manifest.webmanifest", "/sw.js", "/icon-192.png", "/icon-512.png", "/apple-touch-icon.png", "/login"}


def _password() -> str:
    return os.environ.get("MANANA_PASSWORD", "")


def _token() -> str:
    return hmac.new(_password().encode(), b"manana-session", hashlib.sha256).hexdigest()


def _lan_ip() -> str:
    """IP ноутбука в локальной сети — по нему телефон в том же Wi-Fi откроет приложение."""
    with contextlib.suppress(OSError), socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    return ""
MAX_UPLOAD = 20 * 1024 * 1024
SAMPLE = ROOT / "input" / "requirements.md"
CRIT_JSON = json.dumps({c.code: c.name for c in INDIVIDUAL + SET}, ensure_ascii=False)
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


CHAT_SYSTEM = (
    "Ты — Manana, дружелюбный ИИ-агент и маскот приложения для проверки документов требований "
    "(зелёный пухлик с золотым ростком). Ты проверяешь требования по ISO/IEC/IEEE 29148:2018 и IEEE Std 830-1998: "
    "необходимость, однозначность, полнота, атомарность, выполнимость, проверяемость, корректность, прослеживаемость, "
    "а у набора — полнота, непротиворечивость, понятность, ранжирование. "
    "Отвечай по-русски, тепло, но по делу и коротко: обычно 2–6 предложений или короткий список. "
    "Можно использовать **жирный** и списки через «- ». Говори о себе в женском роде. "
    "Если ниже есть данные отчёта — опирайся только на них, ссылайся на номера замечаний (V-…) и требований (R-…), "
    "ничего не выдумывай. Если отчёта нет — помогай с формулировкой требований и объясняй, как пользоваться приложением: "
    "загрузить файл (.pdf, .docx, .md, .txt, .html), нажать «Проверить документ», дождаться отчёта 1–5 минут. "
    "На темы, не связанные с требованиями и разработкой ПО, вежливо возвращай разговор к делу."
)


def _report_context(run_id: str | None) -> str:
    """Короткая выжимка отчёта для чата, чтобы модель отвечала по конкретному документу."""
    if not run_id or not re.fullmatch(r"[0-9a-f]{32}", run_id):
        return ""
    f = RUNS / run_id / "report.json"
    if not f.exists():
        return ""
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    reqs = {r["rid"]: r for r in d.get("requirements", [])}
    issues, seen = [], set()
    for r in list(d.get("requirement_results", {}).values()) + [d.get("set_result", {})]:
        for i in r.get("issues", []):
            if i.get("status") != "rejected" and i["iid"] not in seen:
                seen.add(i["iid"])
                issues.append(i)
    order = {"critical": 0, "major": 1, "minor": 2}
    issues.sort(key=lambda i: order.get(i.get("severity"), 3))
    lines = [f"ДОКУМЕНТ: {d.get('run', {}).get('document_title') or d.get('run', {}).get('document_name')}",
             f"ВЕРДИКТ: {d.get('verdict')}", f"ВЫВОД: {d.get('review', {}).get('summary', '')}",
             "ПРИОРИТЕТЫ: " + " | ".join(p.get("text", "") for p in d.get("review", {}).get("priorities", [])),
             f"ТРЕБОВАНИЙ: {len(reqs)}; ЗАМЕЧАНИЙ: {len(issues)}", "ТРЕБОВАНИЯ:"]
    lines += [f"{rid}: {r.get('quote') or r.get('summary')}"[:220] for rid, r in reqs.items()]
    lines.append("ЗАМЕЧАНИЯ:")
    for i in issues[:80]:
        q = "; ".join(f"стр.{loc.get('line_start')} «{loc.get('quote')}»" for loc in i.get("locations", [])[:2])
        lines.append(f"{i['iid']} [{i.get('severity')}, {i.get('criterion')}, {', '.join(i.get('req_ids') or []) or 'набор'}] "
                     f"{i.get('problem')} ИСПРАВИТЬ: {i.get('fix')} ГДЕ: {q}"[:700])
    return "\n".join(lines)[:40000]


def _chat_reply(messages: list, run_id: str | None) -> str:
    history = []
    for m in messages[-16:]:
        who = "Пользователь" if m.get("role") == "user" else "Manana"
        history.append(f"{who}: {str(m.get('text', ''))[:2000]}")
    ctx = _report_context(run_id)
    user = (("ДАННЫЕ ОТЧЁТА ПО ПОСЛЕДНЕЙ ПРОВЕРКЕ:\n" + ctx + "\n\n") if ctx else "Отчёта пока нет.\n\n") + \
        "ПЕРЕПИСКА:\n" + "\n".join(history) + "\n\nОтветь на последнее сообщение пользователя как Manana."
    llm = LLMClient(build_llm_config(no_cache=True), verbose=False)
    return llm.complete(CHAT_SYSTEM, user, json_mode=False, stage="chat").strip()


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

    def _authed(self) -> bool:
        if not _password():
            return True
        cookies = dict(c.strip().split("=", 1) for c in (self.headers.get("Cookie") or "").split(";") if "=" in c)
        return hmac.compare_digest(cookies.get("manana", ""), _token())

    def _guard(self) -> bool:
        """True — запрос можно обслуживать; иначе уже отправлена страница входа или 401."""
        if self.path.split("?")[0] in PUBLIC or self._authed():
            return True
        if self.command == "GET" and self.path.split("?")[0] in ("/", "/index.html"):
            self._send(200, LOGIN_PAGE.replace("{{ERR}}", "").replace("{{FAVICON}}", FAVICON).encode(), "text/html; charset=utf-8")
        else:
            self._json({"error": "Нужно войти: обновите страницу и введите пароль."}, 401)
        return False

    def _static(self) -> bool:
        path = self.path.split("?")[0]
        if path == "/manifest.webmanifest":
            self._send(200, MANIFEST.encode(), "application/manifest+json; charset=utf-8")
        elif path == "/sw.js":
            self._send(200, SERVICE_WORKER.encode(), "text/javascript; charset=utf-8", {"Service-Worker-Allowed": "/"})
        elif path in ("/icon-192.png", "/icon-512.png", "/apple-touch-icon.png"):
            f = ICONS / path.lstrip("/")
            if not f.exists():
                self._send(404, b"", "text/plain")
            else:
                self._send(200, f.read_bytes(), "image/png")
        else:
            return False
        return True

    def do_GET(self) -> None:  # noqa: N802
        if self._static() or not self._guard():
            return
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE.replace("{{NAME}}", AGENT_NAME).replace("{{VER}}", __version__)
                              .replace("{{EXT}}", ", ".join(sorted(SUPPORTED)))
                              .replace("{{LOGO}}", logo(32)).replace("{{FAVICON}}", FAVICON)
                              .replace("{{CRIT}}", CRIT_JSON).encode(), "text/html; charset=utf-8")
        if self.path == "/sample":
            if not SAMPLE.exists():
                return self._send(404, b"", "text/plain")
            return self._send(200, SAMPLE.read_bytes(), "text/markdown; charset=utf-8", {"X-Filename": SAMPLE.name})
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

    def do_HEAD(self) -> None:  # noqa: N802 — страница проверяет, есть ли пример
        if self.path == "/sample" and self._authed():
            self.send_response(200 if SAMPLE.exists() else 404)
            self.send_header("Content-Length", "0")
            self.end_headers()
        else:
            self.send_response(405)
            self.end_headers()

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/login":
            size = min(int(self.headers.get("Content-Length") or 0), 4096)
            pw = parse_qs(self.rfile.read(size).decode("utf-8", "replace")).get("password", [""])[0]
            if _password() and hmac.compare_digest(pw, _password()):
                self.send_response(303)
                self.send_header("Location", "/")
                secure = "; Secure" if self.headers.get("X-Forwarded-Proto") == "https" else ""
                self.send_header("Set-Cookie", f"manana={_token()}; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax{secure}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return None
            return self._send(401, LOGIN_PAGE.replace("{{ERR}}", "Неверный пароль").replace("{{FAVICON}}", FAVICON).encode(),
                              "text/html; charset=utf-8")
        if not self._guard():
            return None
        if self.path == "/chat":
            size = int(self.headers.get("Content-Length") or 0)
            if not 0 < size <= 200_000:
                return self._json({"error": "Слишком длинное сообщение."}, 400)
            try:
                data = json.loads(self.rfile.read(size))
                msgs = [m for m in data.get("messages", []) if isinstance(m, dict)]
                if not msgs:
                    return self._json({"error": "Пустое сообщение."}, 400)
                return self._json({"reply": _chat_reply(msgs, data.get("run"))})
            except ValueError:
                return self._json({"error": "Не получилось прочитать запрос."}, 400)
            except LLMError as e:
                return self._json({"error": f"Модель сейчас недоступна: {e}"}, 502)
            except Exception as e:  # noqa: BLE001
                return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
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
    host = os.environ.get("MANANA_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT") or PORT)
    local = host in ("127.0.0.1", "localhost")
    if not local and not _password():
        print("Внимание: приложение открыто в сеть без пароля. Любой, кто откроет ссылку, будет тратить ваш ключ LLM. "
              "Задайте MANANA_PASSWORD.", file=sys.stderr)
    srv = ThreadingHTTPServer((host, port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"{AGENT_NAME} запущена: {url}", flush=True)
    if not local and (ip := _lan_ip()):
        print(f"С телефона в том же Wi-Fi: http://{ip}:{port}/", flush=True)
    print("Чтобы остановить — закройте это окно или нажмите Ctrl+C.", flush=True)
    if local or os.environ.get("MANANA_OPEN_BROWSER") == "1":
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
