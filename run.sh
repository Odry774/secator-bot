#!/usr/bin/env bash
set -euo pipefail
. .venv/bin/activate
# Переменные берутся через python-dotenv в коде
python -m bot.main
