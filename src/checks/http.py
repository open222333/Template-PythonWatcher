import time

import requests

from src.checks.base import Check, CheckResult, Status, evaluate


class HttpCheck(Check):
    """HTTP 狀態碼與回應時間。

    opts: url, expect_status(200), timeout(10), warn_ms, crit_ms
    """

    def run(self) -> CheckResult:
        url = self.opts['url']
        expect = int(self.opts.get('expect_status', '200'))
        timeout = self.opt_float('timeout', 10)
        start = time.monotonic()
        try:
            resp = requests.get(url, timeout=timeout)
        except requests.RequestException as e:
            return CheckResult(Status.CRIT, f'{url} 連線失敗：{type(e).__name__}')
        ms = (time.monotonic() - start) * 1000
        if resp.status_code != expect:
            return CheckResult(Status.CRIT, f'{url} 狀態碼 {resp.status_code}（預期 {expect}）', ms)
        status = evaluate(ms, self.opt_float('warn_ms'), self.opt_float('crit_ms'))
        return CheckResult(status, f'{url} {resp.status_code}，{ms:.0f} ms', ms)
