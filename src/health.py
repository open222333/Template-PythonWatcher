"""Heartbeat：每輪檢查後寫入時間戳；healthcheck 判斷是否在期限內。"""
import os
import time


def beat(path: str) -> None:
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(str(time.time()))


def is_healthy(path: str, max_age: float) -> bool:
    try:
        with open(path, encoding='utf-8') as f:
            last = float(f.read().strip())
    except (OSError, ValueError):
        return False
    return time.time() - last <= max_age
