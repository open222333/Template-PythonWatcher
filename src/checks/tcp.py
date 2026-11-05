import socket
import time

from src.checks.base import Check, CheckResult, Status


class TcpCheck(Check):
    """TCP 埠是否可連線。opts: host, port, timeout(5)"""

    def run(self) -> CheckResult:
        host, port = self.opts['host'], int(self.opts['port'])
        start = time.monotonic()
        try:
            with socket.create_connection((host, port), timeout=self.opt_float('timeout', 5)):
                pass
        except OSError as e:
            return CheckResult(Status.CRIT, f'{host}:{port} 無法連線：{e}')
        ms = (time.monotonic() - start) * 1000
        return CheckResult(Status.OK, f'{host}:{port} 可連線，{ms:.0f} ms', ms)
