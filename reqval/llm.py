"""Клиент LLM без внешних SDK (только стандартная библиотека).

Провайдеры:
  gemini    — Google AI Studio (Gemini API), рекомендуемый бесплатный вариант
  openai    — OpenAI или любой OpenAI-совместимый endpoint (OpenRouter, Groq, vLLM, LM Studio)
  anthropic — Anthropic Messages API
  ollama    — локальная модель через Ollama

Особенности:
  * temperature = 0 для воспроизводимости;
  * повтор при 429/5xx с экспоненциальной задержкой (учитывается retryDelay Gemini);
  * минимальный интервал между запросами (бесплатные лимиты RPM);
  * дисковый кэш ответов (.cache/) — повторный прогон того же документа той же
    моделью не тратит квоту и даёт тот же отчёт.
"""
from __future__ import annotations

import hashlib
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .jsonutil import parse_json


def _ssl_context() -> ssl.SSLContext:
    """Корневые сертификаты из certifi: Python с python.org на macOS своих не имеет."""
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_SSL = _ssl_context()


class LLMError(RuntimeError):
    pass


@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.0
    max_output_tokens: int = 32768
    timeout: int = 300
    min_interval: float = 0.0
    max_retries: int = 6
    cache_dir: Optional[Path] = None
    # запасные модели того же провайдера: на них переключаемся, если основная
    # снята (404) или перегружена (3 подряд ответа 429/5xx)
    fallback_models: tuple[str, ...] = ()
    switch_after: int = 3
    max_wait: float = 120.0       # дольше не ждём retryDelay: сразу запасная модель или ошибка


DEFAULTS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "ollama": "http://localhost:11434",
}


class LLMClient:
    def __init__(self, cfg: LLMConfig, verbose: bool = True):
        if cfg.provider not in DEFAULTS:
            raise LLMError(f"Неизвестный провайдер: {cfg.provider}. Доступны: {', '.join(DEFAULTS)}")
        if cfg.provider != "ollama" and not cfg.api_key:
            raise LLMError(
                f"Не задан API-ключ для провайдера {cfg.provider}. Скопируйте .env.example в .env и укажите ключ."
            )
        self.cfg = cfg
        self.base = (cfg.base_url or DEFAULTS[cfg.provider]).rstrip("/")
        self.verbose = verbose
        self.calls = 0
        self.cache_hits = 0
        self._last = 0.0
        self.models_used: list[str] = [cfg.model]
        self._fallbacks = [m for m in cfg.fallback_models if m and m != cfg.model]
        self._dead: set[str] = set()  # модели с исчерпанной квотой или снятые (404)

    # ------------------------------------------------------------------ public
    @property
    def label(self) -> str:
        return f"{self.cfg.provider}:{self.cfg.model}"

    def complete_json(self, system: str, user: str, stage: str = "") -> Any:
        """Запрос с ожиданием JSON-ответа. При невалидном JSON — одна попытка исправления."""
        text = self.complete(system, user, json_mode=True, stage=stage)
        try:
            return parse_json(text)
        except ValueError:
            self._log(f"  [{stage}] ответ не является валидным JSON — прошу модель исправить")
            fix_user = (
                user
                + "\n\n---\nТвой предыдущий ответ не был валидным JSON. Верни ТОЛЬКО валидный JSON "
                "по той же схеме, без пояснений и без markdown.\nПредыдущий ответ:\n"
                + text[:20000]
            )
            text2 = self.complete(system, fix_user, json_mode=True, stage=stage + ":repair")
            return parse_json(text2)

    def complete(self, system: str, user: str, json_mode: bool = True, stage: str = "") -> str:
        key = self._cache_key(system, user, json_mode)
        cached = self._cache_get(key)
        if cached is not None:
            self.cache_hits += 1
            self._log(f"  [{stage}] ответ из кэша")
            return cached

        fn = getattr(self, f"_call_{self.cfg.provider}")
        attempt = 0
        while True:
            self._throttle()
            attempt += 1
            t0 = time.time()
            try:
                text = fn(system, user, json_mode)
                self.calls += 1
                self._log(f"  [{stage}] ответ модели получен за {time.time() - t0:.1f} с")
                self._cache_put(self._cache_key(system, user, json_mode), text)
                return text
            except _ModelGone as e:
                self._dead.add(self.cfg.model)
                if not self._switch_model(stage, str(e)) and not self._back_to_alive(stage):
                    raise LLMError(str(e)) from e
                attempt = 0
            except _Retryable as e:
                delay = e.delay
                # квота исчерпана надолго (Gemini просит ждать часы) — ждать бессмысленно
                if delay and delay > self.cfg.max_wait:
                    reason = f"{e}, лимит исчерпан (ждать {delay / 3600:.1f} ч)"
                    self._dead.add(self.cfg.model)
                    if self._switch_model(stage, reason):
                        attempt = 0
                        continue
                    # запасных нет — возвращаемся к модели, которая была лишь перегружена, и повторяем
                    if not self._back_to_alive(stage):
                        raise LLMError(f"Модель {self.cfg.model}: {reason}. Повторите позже или задайте другую модель.") from e
                    delay = None
                elif attempt >= self.cfg.switch_after and self._switch_model(stage, str(e)):
                    attempt = 0
                    continue
                if attempt > self.cfg.max_retries:
                    raise LLMError(f"Модель недоступна после {attempt} попыток: {e}") from e
                delay = delay or min(60.0, 2.0 ** attempt)
                self._log(f"  [{stage}] {e} — повтор через {delay:.0f} с (попытка {attempt}/{self.cfg.max_retries})")
                time.sleep(delay)

    def _switch_model(self, stage: str, reason: str) -> bool:
        """Переключиться на следующую запасную модель до конца прогона. False — запасных не осталось."""
        if not self._fallbacks:
            return False
        old, self.cfg.model = self.cfg.model, self._fallbacks.pop(0)
        self.models_used.append(self.cfg.model)
        self._log(f"  [{stage}] {old}: {reason[:120]} — переключаюсь на {self.cfg.model}")
        return True

    def _back_to_alive(self, stage: str) -> bool:
        """Вернуться к последней модели, у которой не исчерпана квота (была лишь перегружена)."""
        alive = [m for m in reversed(self.models_used) if m not in self._dead]
        if not alive:
            return False
        old, self.cfg.model = self.cfg.model, alive[0]
        self.models_used.append(self.cfg.model)
        self._log(f"  [{stage}] у запасных моделей нет квоты — возвращаюсь к {self.cfg.model} ({old} недоступна)")
        return True

    # --------------------------------------------------------------- providers
    def _call_gemini(self, system: str, user: str, json_mode: bool) -> str:
        url = f"{self.base}/models/{self.cfg.model}:generateContent"
        gen: dict[str, Any] = {
            "temperature": self.cfg.temperature,
            "maxOutputTokens": self.cfg.max_output_tokens,
        }
        if json_mode:
            gen["responseMimeType"] = "application/json"
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": gen,
        }
        data = self._post(url, body, {"x-goog-api-key": self.cfg.api_key})
        try:
            cand = data["candidates"][0]
            parts = cand.get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        except (KeyError, IndexError) as e:
            raise LLMError(f"Неожиданный ответ Gemini: {json.dumps(data, ensure_ascii=False)[:500]}") from e
        if not text:
            reason = cand.get("finishReason", "?")
            if reason == "MAX_TOKENS":
                raise LLMError("Ответ Gemini обрезан по лимиту токенов (увеличьте LLM_MAX_OUTPUT_TOKENS).")
            raise _Retryable(f"пустой ответ Gemini (finishReason={reason})")
        return text

    def _call_openai(self, system: str, user: str, json_mode: bool) -> str:
        url = f"{self.base}/chat/completions"
        body: dict[str, Any] = {
            "model": self.cfg.model,
            "temperature": self.cfg.temperature,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        data = self._post(url, body, {"Authorization": f"Bearer {self.cfg.api_key}"})
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as e:
            raise LLMError(f"Неожиданный ответ OpenAI: {json.dumps(data, ensure_ascii=False)[:500]}") from e

    def _call_anthropic(self, system: str, user: str, json_mode: bool) -> str:
        url = f"{self.base}/messages"
        body = {
            "model": self.cfg.model,
            "max_tokens": min(self.cfg.max_output_tokens, 32000),
            "temperature": self.cfg.temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {"x-api-key": self.cfg.api_key, "anthropic-version": "2023-06-01"}
        data = self._post(url, body, headers)
        try:
            return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        except KeyError as e:
            raise LLMError(f"Неожиданный ответ Anthropic: {json.dumps(data, ensure_ascii=False)[:500]}") from e

    def _call_ollama(self, system: str, user: str, json_mode: bool) -> str:
        url = f"{self.base}/api/chat"
        body: dict[str, Any] = {
            "model": self.cfg.model,
            "stream": False,
            "options": {"temperature": self.cfg.temperature, "num_ctx": 32768},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        if json_mode:
            body["format"] = "json"
        data = self._post(url, body, {})
        return data.get("message", {}).get("content", "")

    # ------------------------------------------------------------------ http
    def _post(self, url: str, body: dict, headers: dict) -> dict:
        req = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout, context=_SSL) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            payload = e.read().decode("utf-8", errors="replace")
            if e.code == 429 or e.code >= 500:
                raise _Retryable(f"HTTP {e.code}", _retry_delay(payload, e.headers)) from e
            if e.code == 404 and self.cfg.provider != "ollama":
                raise _ModelGone(f"модель {self.cfg.model} недоступна (HTTP 404): {payload[:300]}") from e
            raise LLMError(f"HTTP {e.code} от {self.cfg.provider}: {payload[:800]}") from e
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            raise _Retryable(f"сетевая ошибка: {e}") from e

    # -------------------------------------------------------------- plumbing
    def _throttle(self) -> None:
        gap = self.cfg.min_interval - (time.time() - self._last)
        if gap > 0:
            time.sleep(gap)
        self._last = time.time()

    def _cache_key(self, system: str, user: str, json_mode: bool) -> str:
        h = hashlib.sha256()
        for part in (self.cfg.provider, self.cfg.model, str(self.cfg.temperature), str(json_mode), system, user):
            h.update(part.encode("utf-8"))
            h.update(b"\x00")
        return h.hexdigest()

    def _cache_get(self, key: str) -> Optional[str]:
        if not self.cfg.cache_dir:
            return None
        p = self.cfg.cache_dir / f"{key}.json"
        if p.exists():
            try:
                return json.loads(p.read_text("utf-8"))["text"]
            except Exception:
                return None
        return None

    def _cache_put(self, key: str, text: str) -> None:
        if not self.cfg.cache_dir:
            return
        self.cfg.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.cfg.cache_dir / f"{key}.json").write_text(
            json.dumps({"model": self.label, "text": text}, ensure_ascii=False), "utf-8"
        )

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg, file=sys.stderr, flush=True)


class _Retryable(Exception):
    def __init__(self, msg: str, delay: Optional[float] = None):
        super().__init__(msg)
        self.delay = delay


class _ModelGone(Exception):
    """Модель снята или не существует — повторять бессмысленно, нужна другая."""


def _retry_delay(payload: str, headers) -> Optional[float]:
    m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', payload)
    if m:
        return float(m.group(1)) + 1
    ra = headers.get("Retry-After") if headers else None
    if ra and ra.isdigit():
        return float(ra)
    return None
