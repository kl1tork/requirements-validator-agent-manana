#!/usr/bin/env bash
# Полный прогон одной командой: bash run.sh [файл требований] [файл отчёта]
set -e
cd "$(dirname "$0")"
IN="${1:-input/requirements.md}"
OUT="${2:-reports/report.md}"

if [ ! -d .venv ]; then
  echo "Создаю виртуальное окружение и ставлю зависимости..."
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
fi
if grep -q "your_gemini_api_key_here" .env; then
  echo
  echo ">>> Вставьте ключ Gemini в файл .env вместо your_gemini_api_key_here, сохраните и запустите: bash run.sh"
  (command -v open >/dev/null && open -e .env) || true
  exit 1
fi

.venv/bin/python -m reqval "$IN" "$OUT"
echo
echo "Отчёт: $OUT"
