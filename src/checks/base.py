from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum


class Status(IntEnum):
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3   # 檢查本身執行失敗（例外、設定錯誤）


@dataclass
class CheckResult:
    status: Status
    message: str
    value: float | None = None


def evaluate(value: float, warn: float | None, crit: float | None) -> Status:
    """數值越大越嚴重的門檻判斷。"""
    if crit is not None and value >= crit:
        return Status.CRIT
    if warn is not None and value >= warn:
        return Status.WARN
    return Status.OK


class Check(ABC):
    """一個檢查項目。opts 來自 conf/config.ini 的 [check:<name>] 區段。"""

    def __init__(self, name: str, opts: dict[str, str]):
        self.name = name
        self.opts = opts

    def opt_float(self, key: str, default: float | None = None) -> float | None:
        raw = self.opts.get(key)
        return float(raw) if raw not in (None, '') else default

    @abstractmethod
    def run(self) -> CheckResult:
        ...

    def safe_run(self) -> CheckResult:
        try:
            return self.run()
        except Exception as e:  # noqa: BLE001 - 檢查失敗轉為 UNKNOWN
            return CheckResult(Status.UNKNOWN, f'檢查執行失敗：{type(e).__name__}: {e}')
