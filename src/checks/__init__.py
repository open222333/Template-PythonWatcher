"""檢查項目註冊表。新增檢查：繼承 Check、實作 run()，並加入 REGISTRY。"""
from src.checks.base import Check, CheckResult, Status
from src.checks.disk import DiskCheck
from src.checks.http import HttpCheck
from src.checks.tcp import TcpCheck

REGISTRY: dict[str, type[Check]] = {
    'http': HttpCheck,
    'tcp': TcpCheck,
    'disk': DiskCheck,
}

__all__ = ['Check', 'CheckResult', 'Status', 'REGISTRY']
