import asyncio
import os
import re
import shutil
import zipfile
from typing import Optional

def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def sanitize_tag(tag: str) -> str:
    tag = tag.strip()
    tag = re.sub(r"[^A-Za-z0-9._-]+", "-", tag)
    return tag or "main"

async def extract_with_7z(archive_path: str, out_dir: str, password: Optional[str]=None) -> tuple[bool, str]:
    """Распаковка через 7z. Возвращает (ok, msg)."""
    ensure_dir(out_dir)
    cmd = ["7z", "x", "-y", f"-o{out_dir}", archive_path]
    if password:
        cmd.insert(2, f"-p{password}")
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    out, err = await proc.communicate()
    code = proc.returncode
    text = (out + err).decode(errors="ignore")
    if code == 0:
        return True, "ok"
    if "Wrong password" in text or "Can not open encrypted archive" in text or "Data Error" in text:
        return False, "password_required_or_wrong"
    return False, f"extract_failed: rc={code}"

def _zip_dir(src_dir: str, zip_path: str):
    tmp = zip_path + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(src_dir):
            for f in files:
                full = os.path.join(root, f)
                rel  = os.path.relpath(full, src_dir)
                zf.write(full, arcname=rel)
    os.replace(tmp, zip_path)

async def create_zip(src_dir: str, zip_path: str):
    _zip_dir(src_dir, zip_path)

def rm_tree(p: str):
    if os.path.isdir(p):
        shutil.rmtree(p, ignore_errors=True)
    elif os.path.isfile(p):
        os.remove(p)
