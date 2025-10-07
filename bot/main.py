import asyncio
import os
import uuid
from datetime import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, FSInputFile

from .config import CFG
from .counters import (
    get_next_number, set_counter, get_status,
    set_chat_tag, get_chat_tag,
    set_last_pack_info, get_last_pack_info, today_key
)
from .archive_utils import (
    extract_with_7z, create_zip, rm_tree, ensure_dir, sanitize_tag
)
from .sorter_universal import process_pack
from .antisecator_new_lib import run_antisecator

dp = Dispatcher()

WORK_DIR = os.path.join(CFG.data_dir, "work")
BASES_DIR = os.path.join(CFG.data_dir, "bases")
OUT_DIR = os.path.join(CFG.data_dir, "outgoing")
ensure_dir(WORK_DIR); ensure_dir(BASES_DIR); ensure_dir(OUT_DIR)

# Память для ожидания пароля: chat_id -> dict
PENDING = {}

def moscow_now() -> datetime:
    return datetime.now(CFG.tz_moscow)

def _pending_submission_dt(st: dict) -> datetime:
    iso = st.get("dt_iso")
    if iso:
        try:
            return datetime.fromisoformat(iso)
        except ValueError:
            pass
    day = st.get("day")
    if day:
        try:
            return datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=CFG.tz_moscow)
        except ValueError:
            pass
    return moscow_now()

def pack_folder_name(tag: str, n: int, dt: datetime) -> str:
    date_str = dt.strftime("%d.%m")
    return f"Input logs {tag}-{n}-pack{date_str}"

def raw_pack_zip_name(tag: str, n: int, dt: datetime) -> str:
    date_str = dt.strftime("%d.%m")
    return f"{tag}-{n}-raw-pack{date_str}.zip"

def logs_zip_name(tag: str, n: int, dt: datetime) -> str:
    date_str = dt.strftime("%d.%m")
    return f"{tag}-{n}-logs{date_str}.zip"

@dp.message(Command("start"))
async def cmd_start(m: Message):
    await m.answer(
        "Готов. Команды:\n"
        "/tag <supplier>\n"
        "/setcounter <supplier> <n>\n"
        "/status\n"
        "/cancel\n\n"
        "Пришлите архив (ZIP/RAR/7Z). Если нужен пароль — пришлю запрос."
    )

@dp.message(Command("tag"))
async def cmd_tag(m: Message, command: CommandObject):
    if not command.args:
        await m.answer("Укажите тег: /tag <supplier>")
        return
    tag = sanitize_tag(command.args.strip())
    set_chat_tag(m.chat.id, tag)
    await m.answer(f"Тег установлен: {tag}")

@dp.message(Command("setcounter"))
async def cmd_setcounter(m: Message, command: CommandObject):
    if not command.args:
        await m.answer("Формат: /setcounter <supplier> <n>")
        return
    parts = command.args.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await m.answer("Формат: /setcounter <supplier> <n>")
        return
    tag = sanitize_tag(parts[0])
    n = int(parts[1])
    set_counter(tag, moscow_now(), n)
    await m.answer(f"Счётчик для {tag} на сегодня установлен: {n}")

@dp.message(Command("status"))
async def cmd_status(m: Message):
    st = get_status(moscow_now())
    if not st:
        await m.answer("Сегодня счётчики пусты.")
        return
    lines = [f"{k}: next={v}" for k, v in st.items()]
    await m.answer("Статус:\n" + "\n".join(lines))

@dp.message(Command("cancel"))
async def cmd_cancel(m: Message):
    PENDING.pop(m.chat.id, None)
    await m.answer("Ок, отменил ожидание пароля.")

def _get_tag_from_message(m: Message) -> str | None:
    # Из подписи вида "tag=huyar" или из установленного чатом тэга.
    tag = None
    if m.caption:
        for tok in m.caption.split():
            if tok.startswith("tag="):
                tag = tok.split("=", 1)[1].strip()
                break
    return sanitize_tag(tag) if tag else get_chat_tag(m.chat.id)

async def _download_document(m: Message, path: str):
    file = await m.bot.get_file(m.document.file_id)
    await m.bot.download_file(file.file_path, destination=path)

@dp.message(F.document)
async def on_document(m: Message):
    name = m.document.file_name or "file.bin"
    lower = name.lower()
    is_archive = lower.endswith((".zip", ".rar", ".7z"))
    if not is_archive:
        await m.answer("Пришлите .zip/.rar/.7z")
        return

    tag = _get_tag_from_message(m)
    if not tag:
        await m.answer("Сначала установите тег: /tag <supplier> или добавьте в подпись `tag=<supplier>`.")
        return

    dt = moscow_now()
    n = get_next_number(tag, dt)  # бронируем номер
    pack_dir_name = pack_folder_name(tag, n, dt)
    pack_dir = os.path.join(BASES_DIR, pack_dir_name)
    ensure_dir(pack_dir)

    tmp_id = uuid.uuid4().hex
    tmp_path = os.path.join(WORK_DIR, f"{tmp_id}-{name}")
    await _download_document(m, tmp_path)

    ok, msg = await extract_with_7z(tmp_path, pack_dir, password=None)
    if not ok and msg == "password_required_or_wrong":
        # запросим пароль
        PENDING[m.chat.id] = {
            "type": "extract",
            "tmp_path": tmp_path,
            "pack_dir": pack_dir,
            "tag": tag,
            "n": n,
            "day": today_key(dt),
            "dt_iso": dt.isoformat(),
            "tries": 0,
            "original_name": name,
        }
        await m.answer("Архив защищён. Пришлите пароль одним сообщением или /cancel.")
        return
    elif not ok:
        await m.answer(f"Не удалось распаковать архив (код).")
        rm_tree(tmp_path); rm_tree(pack_dir)
        return

    # Успех распаковки → прогон сортёром
    sorted_dir = os.path.join(WORK_DIR, f"sorted-{tmp_id}")
    copied = process_pack(pack_dir, sorted_dir)
    zip_name = raw_pack_zip_name(tag, n, dt)
    zip_path = os.path.join(OUT_DIR, zip_name)

    if copied == 0:
        await create_zip(pack_dir, zip_path)
    else:
        await create_zip(sorted_dir, zip_path)

    set_last_pack_info(m.chat.id, tag, n, today_key(dt))
    await m.answer_document(FSInputFile(zip_path), caption=f"{zip_name}")

    # cleanup
    rm_tree(tmp_path); rm_tree(sorted_dir)

@dp.message(F.text & (F.chat.id.func(lambda cid: cid in PENDING)))
async def on_password(m: Message):
    st = PENDING.get(m.chat.id)
    if not st or st.get("type") != "extract":
        return
    pwd = m.text.strip()
    st["tries"] += 1
    ok, msg = await extract_with_7z(st["tmp_path"], st["pack_dir"], password=pwd)
    if not ok:
        if st["tries"] >= 3:
            await m.answer("Пароль неверный. Отменяю.")
            rm_tree(st["tmp_path"]); rm_tree(st["pack_dir"])
            PENDING.pop(m.chat.id, None)
            return
        await m.answer("Неверный пароль. Попробуйте ещё раз или /cancel.")
        return

    # успешная распаковка — продолжим как обычно
    tag = st["tag"]; n = st["n"]
    dt = _pending_submission_dt(st)
    day_key = st.get("day") or today_key(dt)
    sorted_dir = os.path.join(WORK_DIR, f"sorted-{uuid.uuid4().hex}")
    copied = process_pack(st["pack_dir"], sorted_dir)
    zip_name = raw_pack_zip_name(tag, n, dt)
    zip_path = os.path.join(OUT_DIR, zip_name)
    if copied == 0:
        await create_zip(st["pack_dir"], zip_path)
    else:
        await create_zip(sorted_dir, zip_path)
    set_last_pack_info(m.chat.id, tag, n, day_key)
    await m.answer_document(FSInputFile(zip_path), caption=f"{zip_name}")
    rm_tree(st["tmp_path"]); rm_tree(sorted_dir)
    PENDING.pop(m.chat.id, None)

@dp.message(F.document & F.document.file_name.regex("(?i)\.txt(\.zip|\.rar|\.7z)?$") | (F.caption and F.caption.lower().contains("txt")))
async def on_txt_pack(m: Message):
    """Принимаем архив с .txt. Берём последний pack-info для чата (tag, n, day),
    запускаем Антисекатор по всем 'Input logs*' в BASES_DIR."""
    if not m.document:
        return

    last = get_last_pack_info(m.chat.id)
    tag = _get_tag_from_message(m) or (last and last["tag"])
    if not tag:
        await m.answer("Не вижу тега поставщика. Укажите /tag <supplier> или подпись `tag=<supplier>`.")
        return

    dt = moscow_now()
    if last and last["tag"] == tag and last["day"] == today_key(dt):
        n = last["n"]
    else:
        from .counters import _load, _save, today_key, get_next_number, set_counter
        _ = get_next_number(tag, dt)
        s = _load()
        day = today_key(dt)
        n = s["counters"][day][tag] - 1
        set_counter(tag, dt, n)  # фиксируем как «следующее» = n

    tmp_id = uuid.uuid4().hex
    tmp_path = os.path.join(WORK_DIR, f"{tmp_id}-{m.document.file_name}")
    await _download_document(m, tmp_path)

    txt_dir = os.path.join(WORK_DIR, f"txt-{tmp_id}")
    os.makedirs(txt_dir, exist_ok=True)
    ok, msg = await extract_with_7z(tmp_path, txt_dir, password=None)
    if not ok and msg == "password_required_or_wrong":
        PENDING[m.chat.id] = {
            "type": "txtpwd",
            "tmp_path": tmp_path,
            "txt_dir": txt_dir,
            "tag": tag,
            "n": n,
        }
        await m.answer("Архив с .txt защищён. Пришлите пароль одним сообщением или /cancel.")
        return
    elif not ok:
        await m.answer("Не удалось распаковать архив с .txt.")
        rm_tree(tmp_path); rm_tree(txt_dir)
        return

    out_tmp = os.path.join(WORK_DIR, f"anti-{tmp_id}")
    os.makedirs(out_tmp, exist_ok=True)
    zips = run_antisecator(txt_list_dir=txt_dir, bases_parent_dir=BASES_DIR, output_root=out_tmp, prefix="Input logs")

    if not zips:
        await m.answer("Антисекатор: ничего не собрано.")
        rm_tree(tmp_path); rm_tree(txt_dir); rm_tree(out_tmp)
        return

    zip_name = logs_zip_name(tag, n, dt)
    zip_path = os.path.join(OUT_DIR, zip_name)
    await create_zip(out_tmp, zip_path)

    await m.answer_document(FSInputFile(zip_path), caption=zip_name)
    rm_tree(tmp_path); rm_tree(txt_dir); rm_tree(out_tmp)

@dp.message(F.text & (F.chat.id.func(lambda cid: cid in PENDING)))
async def on_txt_password(m: Message):
    st = PENDING.get(m.chat.id)
    if not st or st.get("type") != "txtpwd":
        return
    pwd = m.text.strip()
    ok, msg = await extract_with_7z(st["tmp_path"], st["txt_dir"], password=pwd)
    if not ok:
        await m.answer("Неверный пароль или ошибка распаковки. Отменяю.")
        rm_tree(st["tmp_path"]); rm_tree(st["txt_dir"])
        PENDING.pop(m.chat.id, None)
        return

    dt = moscow_now()
    out_tmp = os.path.join(WORK_DIR, f"anti-{uuid.uuid4().hex}")
    os.makedirs(out_tmp, exist_ok=True)
    zips = run_antisecator(txt_list_dir=st["txt_dir"], bases_parent_dir=BASES_DIR, output_root=out_tmp, prefix="Input logs")
    if not zips:
        await m.answer("Антисекатор: ничего не собрано.")
        rm_tree(st["tmp_path"]); rm_tree(st["txt_dir"]); rm_tree(out_tmp)
        PENDING.pop(m.chat.id, None)
        return

    zip_name = logs_zip_name(st["tag"], st["n"], dt)
    zip_path = os.path.join(OUT_DIR, zip_name)
    await create_zip(out_tmp, zip_path)
    await m.answer_document(FSInputFile(zip_path), caption=zip_name)
    rm_tree(st["tmp_path"]); rm_tree(st["txt_dir"]); rm_tree(out_tmp)
    PENDING.pop(m.chat.id, None)

async def main():
    session = AiohttpSession(api=TelegramAPIServer.from_base(CFG.api_base))
    bot = Bot(CFG.bot_token, session=session)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
