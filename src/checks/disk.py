import shutil

from src.checks.base import Check, CheckResult, evaluate


class DiskCheck(Check):
    """磁碟使用率。opts: path(/), warn_percent(80), crit_percent(90)"""

    def run(self) -> CheckResult:
        path = self.opts.get('path', '/')
        usage = shutil.disk_usage(path)
        percent = usage.used / usage.total * 100
        status = evaluate(percent, self.opt_float('warn_percent', 80), self.opt_float('crit_percent', 90))
        return CheckResult(status, f'{path} 使用率 {percent:.1f}%', percent)
