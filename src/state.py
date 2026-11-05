"""告警狀態與去重。

規則：
- 狀態改變（OK→WARN、WARN→CRIT、CRIT→OK…）→ 立即通知
- 持續異常且距上次通知超過 remind_interval 秒 → 提醒通知
- 持續 OK → 不通知
"""
import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass

from src.checks.base import CheckResult, Status


@dataclass
class Entry:
    status: int = Status.OK
    since: float = 0.0
    last_notified: float = 0.0


class AlertState:
    def __init__(self, path: str, remind_interval: int = 1800):
        self.path = path
        self.remind_interval = remind_interval
        self.entries: dict[str, Entry] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, encoding='utf-8') as f:
                raw = json.load(f)
            self.entries = {k: Entry(**v) for k, v in raw.items()}
        except (OSError, ValueError, TypeError):
            self.entries = {}   # 狀態檔損毀時重新開始，不中斷監控

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path) or '.', suffix='.tmp')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump({k: asdict(v) for k, v in self.entries.items()}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)   # 原子寫入，避免中途中斷留下壞檔

    def update(self, name: str, result: CheckResult, now: float | None = None) -> str | None:
        """更新狀態，回傳應發送的通知類型：'alert' / 'recovery' / 'remind' / None。"""
        now = now if now is not None else time.time()
        prev = self.entries.get(name)
        status = int(result.status)

        if prev is None:
            self.entries[name] = Entry(status, now, now if status != Status.OK else 0.0)
            return 'alert' if status != Status.OK else None

        if status != prev.status:
            kind = 'recovery' if status == Status.OK else 'alert'
            self.entries[name] = Entry(status, now, now)
            return kind

        if status != Status.OK and now - prev.last_notified >= self.remind_interval:
            prev.last_notified = now
            return 'remind'
        return None
