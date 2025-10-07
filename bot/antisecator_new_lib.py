# Адаптация под Linux и вызов как функции.
import os
import shutil
import zipfile

def read_wanted_from_txt(txt_list_dir: str) -> set[str]:
    return {
        os.path.splitext(f)[0]
        for f in os.listdir(txt_list_dir)
        if f.lower().endswith(".txt")
    }

def find_input_bases(parent_dir: str, prefix: str) -> list[tuple[str, str]]:
    res = []
    for name in os.listdir(parent_dir):
        full = os.path.join(parent_dir, name)
        if not os.path.isdir(full):
            continue
        if not name.lower().startswith(prefix.lower()):
            continue
        suffix = name[len(prefix):].strip()
        label = "main" if suffix == "" else suffix
        res.append((full, label))
    res.sort(key=lambda x: (x[1] != "main", x[1]))
    return res

def copy_needed_folders(src_root: str, wanted: set[str], dst_root: str) -> int:
    os.makedirs(dst_root, exist_ok=True)
    copied = set()
    for root, dirs, _ in os.walk(src_root):
        for d in dirs:
            if d in wanted and d not in copied:
                src_folder = os.path.join(root, d)
                dst_folder = os.path.join(dst_root, d)
                if os.path.exists(dst_folder):
                    continue
                shutil.copytree(src_folder, dst_folder)
                copied.add(d)
    count = sum(1 for name in os.listdir(dst_root) if os.path.isdir(os.path.join(dst_root, name)))
    return count

def zip_dir(dir_path: str, zip_path: str) -> None:
    tmp_zip = zip_path + ".tmp"
    with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(dir_path):
            for f in files:
                full = os.path.join(root, f)
                rel  = os.path.relpath(full, dir_path)
                zf.write(full, arcname=rel)
    os.replace(tmp_zip, zip_path)

def run_antisecator(txt_list_dir: str, bases_parent_dir: str, output_root: str, prefix: str="Input logs") -> list[str]:
    """Возвращает список путей к созданным ZIP архивам (по лейблам баз)."""
    wanted = read_wanted_from_txt(txt_list_dir)
    if not wanted:
        return []
    bases = find_input_bases(bases_parent_dir, prefix)
    if not bases:
        return []

    os.makedirs(output_root, exist_ok=True)
    created = []
    for src_base_dir, label in bases:
        out_dir = os.path.join(output_root, label)
        os.makedirs(out_dir, exist_ok=True)
        top_level_count = copy_needed_folders(src_base_dir, wanted, out_dir)
        if top_level_count == 0:
            try:
                if os.path.isdir(out_dir) and not os.listdir(out_dir):
                    os.rmdir(out_dir)
            except OSError:
                pass
            continue
        zip_name = f"{top_level_count}-{label}.zip"
        zip_full = os.path.join(output_root, zip_name)
        zip_dir(out_dir, zip_full)
        created.append(zip_full)
    return created
