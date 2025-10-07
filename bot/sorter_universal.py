import os
import shutil
from typing import Optional, Tuple

# Список префиксов объединён из скриптов
ALLOWED_PREFIXES: Tuple[str, ...] = (
    "Gmail_Info",
    "Outlook_Info",
    "[Simple Checker] Google Information",
    "[Simple Checker] Outlook Information",
    "Gmail_Email_Info",
    "Outlook_Email_Info",
    "Gmail",
    "Outlook",
    "[index ",
    "[1", "[2", "[3", "[4", "[5", "[6", "[7", "[8", "[9",
)

def best_matching_txt(dir_path: str) -> Optional[str]:
    best = None
    best_len = 0
    try:
        for name in os.listdir(dir_path):
            if not name.endswith(".txt"):
                continue
            match = 0
            for p in ALLOWED_PREFIXES:
                if name.startswith(p) and len(p) > match:
                    match = len(p)
            if match > 0 and match >= best_len:
                if match > best_len or (best and name < os.path.basename(best)):
                    best = os.path.join(dir_path, name)
                    best_len = match
    except OSError:
        return None
    return best

def unique_path(path: str) -> str:
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    k = 1
    while True:
        trial = f"{base} ({k}){ext}"
        if not os.path.exists(trial):
            return trial
        k += 1

def process_pack(input_root: str, output_root: str) -> int:
    """
    Рекурсивно проходит по вложенным папкам input_root.
    Копирует по одному .txt согласно префиксам в output_root,
    формируя category/account.txt (если есть 2+ уровней) или account.txt.
    Возвращает число скопированных файлов.
    """
    os.makedirs(output_root, exist_ok=True)
    copied = 0
    for root, dirs, files in os.walk(input_root):
        if root == input_root:
            continue
        txt = best_matching_txt(root)
        if not txt:
            continue
        rel = os.path.relpath(root, input_root)
        parts = [p for p in rel.split(os.sep) if p and p != "."]
        account = parts[-1] if parts else os.path.basename(root)
        category = parts[-2] if len(parts) >= 2 else None
        out_dir = os.path.join(output_root, category) if category else output_root
        os.makedirs(out_dir, exist_ok=True)
        dst = unique_path(os.path.join(out_dir, f"{account}.txt"))
        shutil.copy2(txt, dst)
        copied += 1
    return copied
