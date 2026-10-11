"""Atomic JSON writes and serialized read-modify-write updates."""
import json
import os
import tempfile
import threading

_config_lock = threading.RLock()


def save_config_atomic(config, file_path):
    """Replace a JSON file only after writing it completely; propagate failures."""
    file_path = os.path.abspath(file_path)
    with _config_lock:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=os.path.dirname(file_path),
                prefix="." + os.path.basename(file_path) + ".", suffix=".tmp", delete=False,
            ) as stream:
                temp_path = stream.name
                json.dump(config, stream, indent=2, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, file_path)
        finally:
            if temp_path is not None and os.path.exists(temp_path):
                os.unlink(temp_path)


def update_config_atomic(file_path, updates):
    """Apply a mapping or callback without losing another thread's edits."""
    with _config_lock:
        config = {}
        if os.path.exists(file_path):
            with open(file_path, encoding="utf-8") as stream:
                config = json.load(stream)
        if not isinstance(config, dict):
            raise ValueError("配置文件必须是 JSON 对象")
        if callable(updates):
            updates(config)
        else:
            config.update(updates)
        save_config_atomic(config, file_path)
        return config


def validate_config_name(name):
    """Require one portable Windows filename, never a path."""
    import re
    if (not name or name in {".", ".."} or name != name.rstrip(" .")
            or re.search(r'[\\/:*?"<>|\x00-\x1f]', name)
            or name.split(".")[0].upper() in
            {"CON", "PRN", "AUX", "NUL", *{f"COM{i}" for i in range(1, 10)},
             *{f"LPT{i}" for i in range(1, 10)}}):
        raise ValueError("名称必须是有效的文件名，不能包含路径、保留名称或非法字符。")
    return name
