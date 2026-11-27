"""Командная строка: python -m reqval <файл требований> <файл отчёта>"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import build_llm_config, load_env
from .llm import LLMClient, LLMError


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m reqval",
        description="Агент статической проверки требований (ISO/IEC/IEEE 29148:2018, IEEE 830-1998).",
    )
    p.add_argument("input", help="путь к документу требований (.pdf, .md, .txt, .docx, .html)")
    p.add_argument("output", nargs="?", default="reports/report.md",
                   help="путь к файлу отчёта (.md, .html или .json); по умолчанию reports/report.md")
    p.add_argument("--provider", choices=["gemini", "openai", "anthropic", "ollama"],
                   help="провайдер LLM (по умолчанию — из .env: LLM_PROVIDER или первый заданный ключ)")
    p.add_argument("--model", help="имя модели (по умолчанию — из .env)")
    p.add_argument("--env", type=Path, help="путь к .env (по умолчанию ./.env)")
    p.add_argument("--batch-size", type=int, default=6, help="требований в одном запросе к модели (по умолчанию 6)")
    p.add_argument("--segmenter", choices=["llm", "rules"], default="llm",
                   help="нарезка требований моделью (по умолчанию) или только парсером")
    p.add_argument("--no-verify", action="store_true", help="не выполнять проход перепроверки замечаний")
    p.add_argument("--no-cache", action="store_true", help="не использовать кэш ответов модели")
    p.add_argument("-q", "--quiet", action="store_true", help="меньше вывода в консоль")
    args = p.parse_args(argv)

    load_env(args.env)
    try:
        cfg = build_llm_config(args.provider, args.model, args.no_cache)
        llm = LLMClient(cfg, verbose=not args.quiet)
    except (LLMError, ValueError) as e:
        print(f"Ошибка конфигурации: {e}", file=sys.stderr)
        return 2

    from .pipeline import run

    try:
        run(Path(args.input), Path(args.output), llm, segment_mode=args.segmenter,
            batch_size=max(1, args.batch_size), do_verify=not args.no_verify)
    except FileNotFoundError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        return 2
    except LLMError as e:
        print(f"Ошибка обращения к модели: {e}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
