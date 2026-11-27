#!/usr/bin/env bash
# Manana — запуск приложения двойным щелчком (macOS). Откроется страница в браузере.
cd "$(dirname "$0")" || exit 1

if [ ! -d .venv ]; then
  echo "Первый запуск: создаю окружение и ставлю зависимости (1–2 минуты)..."
  python3 -m venv .venv || { echo "Нужен Python 3.10+: https://www.python.org/downloads/"; read -r -p "Нажмите Enter..."; exit 1; }
fi
.venv/bin/pip install -q -r requirements.txt

if [ ! -f .env ]; then cp .env.example .env; fi
if grep -q "your_gemini_api_key_here" .env; then
  echo
  echo ">>> Вставьте ключ Gemini в файл .env вместо your_gemini_api_key_here, сохраните и запустите Manana снова."
  open -e .env
  read -r -p "Нажмите Enter, чтобы закрыть..."
  exit 1
fi

.venv/bin/python -m reqval.web
