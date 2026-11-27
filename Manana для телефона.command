#!/usr/bin/env bash
# Manana с доступом с телефона в том же Wi-Fi. Адрес для телефона появится в этом окне.
cd "$(dirname "$0")" || exit 1
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
MANANA_HOST=0.0.0.0 MANANA_OPEN_BROWSER=1 .venv/bin/python -m reqval.web
