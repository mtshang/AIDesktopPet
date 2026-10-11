"""Safe storage operations for user-edited character images."""
import json
import os
from pathlib import Path

from json_write import save_config_atomic, update_config_atomic, validate_config_name

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".tif", ".tiff"}


def checked_mod_path(base_dir, path):
    base = os.path.normcase(os.path.realpath(base_dir))
    resolved = os.path.normcase(os.path.realpath(path))
    validate_config_name(os.path.basename(os.path.abspath(path)))
    if os.path.dirname(resolved) != base:
        raise ValueError("角色目录必须位于指定 MOD 目录内，不能指向其他位置。")
    return os.path.abspath(path)


def image_relative_path(root, path):
    root = os.path.normcase(os.path.realpath(root))
    path = os.path.normcase(os.path.realpath(path))
    try:
        inside = os.path.commonpath([root, path]) == root and path != root
    except ValueError:
        inside = False
    if not inside or Path(path).suffix.lower() not in IMAGE_SUFFIXES:
        raise ValueError("仅允许清理当前角色目录内的图片。")
    return os.path.relpath(path, root)


def referenced_images(nature, root):
    paths = []
    if nature.get("default_image"):
        paths.append(os.path.join(root, nature["default_image"]))
    for state in ("standing", "thinking", "draging", "error"):
        node = nature.get("file", {}).get(state, {})
        names = [node.get("image", ""), node.get("css_sprites", ""), *node.get("frame", [])]
        paths.extend(os.path.join(root, state, name) for name in names if name)
    return {image_relative_path(root, path) for path in paths}


def save_mod(old_path, new_path, nature, base_dir, config_path, pending_removals):
    old_path = checked_mod_path(base_dir, old_path)
    new_path = checked_mod_path(base_dir, new_path)
    # Validate references before changing anything on disk.
    retained = referenced_images(nature, new_path)
    removals = {image_relative_path(new_path, os.path.join(new_path, item)) for item in pending_removals}
    previous = json.loads(Path(old_path, "nature.json").read_text(encoding="utf-8"))
    renamed = os.path.normcase(old_path) != os.path.normcase(new_path)
    moved = written = False
    try:
        if renamed:
            if os.path.exists(new_path):
                raise FileExistsError("已存在同名角色目录。")
            os.rename(old_path, new_path)
            moved = True
        save_config_atomic(nature, os.path.join(new_path, "nature.json"))
        written = True
        if moved and config_path:
            def rename_active(config):
                if config.get("PET_LAST") == os.path.basename(old_path):
                    config["PET_LAST"] = os.path.basename(new_path)
            update_config_atomic(config_path, rename_active)
    except Exception:
        if moved:
            try:
                if written:
                    save_config_atomic(previous, os.path.join(new_path, "nature.json"))
            finally:
                os.rename(new_path, old_path)
        raise

    warnings = []
    # No old image is removed until both the character and active selection are saved.
    for relative in removals - retained:
        path = os.path.join(new_path, relative)
        try:
            image_relative_path(new_path, path)  # Recheck after a possible rename.
            if os.path.isfile(path):
                os.remove(path)
        except (OSError, ValueError) as exc:
            warnings.append(f"旧图片未能清理：{relative}（{exc}）")
    return "\n".join(warnings)
