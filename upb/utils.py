from __future__ import annotations

import os


def save_debug(debug_dir: str | None, name: str, text: str) -> None:
    if not debug_dir:
        return
    os.makedirs(debug_dir, exist_ok=True)
    path = os.path.join(debug_dir, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
