# tg-packs-bot (Linux + Local Bot API, ZIP output)

Телеграм‑бот для приёма архивов (ZIP/RAR/7Z, с паролем/без), распаковки в пачки
вида `Input logs <tag>-<N>-packDD.MM` по московскому времени, прогонки через
универсальный сортёр, а затем приёма архива с `.txt` и запуска «Антисекатор new`».

Итоговые ответы всегда в ZIP:
- `<tag>-<N>-raw-packDD.MM.zip`
- `<tag>-<N>-logsDD.MM.zip`

## Возможности
- Теги поставщиков, отдельный счётчик паков в сутки на каждый тег.
- Автозапрос пароля, если архив защищён.
- Универсальный сортёр: вытаскивает по одному нужному `.txt` из каждой папки/подпапки.
- Антисекатор: собирает наборы согласно списку `.txt` и упаковывает по базам.
- Оптимизировано под Linux и **локальный Telegram Bot API** (self‑hosted).

## Установка (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install -y python3-venv p7zip-full tzdata
# Рекомендуется для RAR5-архивов (опционально, если rar не раскрывается 7z):
sudo apt install -y p7zip-rar unrar

git clone <ваш-репозиторий> tg-packs-bot
cd tg-packs-bot
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# отредактируйте .env:
# BOT_TOKEN=123456:ABC... (токен бота)
# API_BASE=http://localhost:8081  (ваш локальный Bot API base URL)
# DATA_DIR=/opt/tg-packs-bot/data  (или оставить ./data)

mkdir -p data
./run.sh
```

## Команды бота
- `/tag <supplier>` — установить тег (например: `/tag huyar`).
- `/setcounter <supplier> <n>` — выставить «следующее значение» счётчика на сегодня.
- `/status` — показать счётчики на сегодня.
- `/cancel` — отмена ожидания пароля.

## Пути
- Распакованные базы: `data/bases/Input logs <tag>-<N>-packDD.MM`
- Временные файлы: `data/work/`
- Готовые ответы: `data/outgoing/`
- Состояние/счётчики: `data/state.json`

## Systemd (опционально)
```ini
# /etc/systemd/system/tg-packs-bot.service
[Unit]
Description=Tg Packs Bot
After=network.target

[Service]
WorkingDirectory=/opt/tg-packs-bot
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/tg-packs-bot/.venv/bin/python -m bot.main
Restart=always
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now tg-packs-bot
```
