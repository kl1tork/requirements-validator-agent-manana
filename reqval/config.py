"""Настройки из .env / переменных окружения."""
from __future__ import annotations

import os
from pathlib import Path

from .llm import LLMConfig

ROOT = Path(__file__).resolve().parent.parent

# провайдер -> (переменная ключа, переменная модели, модель по умолчанию, мин. интервал между запросами, с)
PROVIDERS = {
    "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL", "gemini-3.5-flash", 6.5),
    "openai": ("OPENAI_API_KEY", "OPENAI_MODEL", "gpt-4o-mini", 0.0),
    "anthropic": ("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "claude-sonnet-5-5", 0.0),
    "ollama": ("", "OLLAMA_MODEL", "qwen2.5:14b", 0.0),
}

# запасные модели по умолчанию (переопределяются <PROVIDER>_FALLBACK_MODELS через запятую; пусто — без переключения)
DEFAULT_FALLBACKS = {
    "gemini": "gemini-3.6-flash,gemini-3.8-flash",
}


def load_env(path: Path | None = None) -> None:
    """Минимальный загрузчик .env (без зависимости от python-dotenv). Не перезаписывает уже заданные переменные."""
    for p in [path] if path else [Path.cwd() / ".env", ROOT / ".env"]:
        if p and p.exists():
            for raw in p.read_text("utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
            break


def detect_provider() -> str:
    explicit = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if explicit:
        return explicit
    for name, (key_var, *_rest) in PROVIDERS.items():
        if key_var and _real(os.environ.get(key_var, "")):
            return name
    if os.environ.get("OLLAMA_MODEL") or os.environ.get("OLLAMA_BASE_URL"):
        return "ollama"
    return "gemini"


def _real(v: str) -> bool:
    return bool(v) and not v.startswith("your_")


def build_llm_config(provider: str | None = None, model: str | None = None, no_cache: bool = False) -> LLMConfig:
    provider = (provider or detect_provider()).lower()
    if provider not in PROVIDERS:
        raise ValueError(f"Неизвестный провайдер {provider}. Доступны: {', '.join(PROVIDERS)}")
    key_var, model_var, default_model, interval = PROVIDERS[provider]
    key = os.environ.get(key_var, "") if key_var else ""
    if not _real(key):
        key = ""
    base_url = os.environ.get(f"{provider.upper()}_BASE_URL", "")
    cache_dir = None if no_cache or os.environ.get("LLM_CACHE", "1") == "0" else ROOT / ".cache"
    fallbacks = os.environ.get(f"{provider.upper()}_FALLBACK_MODELS", DEFAULT_FALLBACKS.get(provider, ""))
    return LLMConfig(
        provider=provider,
        model=model or os.environ.get(model_var) or default_model,
        api_key=key,
        base_url=base_url,
        temperature=float(os.environ.get("LLM_TEMPERATURE", "0")),
        max_output_tokens=int(os.environ.get("LLM_MAX_OUTPUT_TOKENS", "32768")),
        timeout=int(os.environ.get("LLM_TIMEOUT", "300")),
        min_interval=float(os.environ.get("LLM_MIN_INTERVAL", str(interval))),
        cache_dir=cache_dir,
        fallback_models=tuple(m.strip() for m in fallbacks.split(",") if m.strip()),
    )
