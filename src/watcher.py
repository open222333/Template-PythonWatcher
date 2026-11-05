import logging
import os
import time

from src import BASE_DIR, config, get_int, get_setting
from src.checks import REGISTRY, Check, CheckResult, Status
from src.health import beat
from src.notify import Notifier, send_all
from src.state import AlertState

logger = logging.getLogger(__name__)

ICONS = {Status.OK: '✅', Status.WARN: '⚠️', Status.CRIT: '🔴', Status.UNKNOWN: '❓'}
TITLES = {'alert': '告警', 'recovery': '恢復', 'remind': '持續異常'}


def _path(key: str, default: str) -> str:
    p = get_setting('WATCHER', key, default)
    return p if os.path.isabs(p) else os.path.join(BASE_DIR, p)


def load_checks(cfg=config) -> list[Check]:
    """讀取 [check:<name>] 區段；enabled = false 的略過。"""
    checks: list[Check] = []
    for section in cfg.sections():
        if not section.startswith('check:'):
            continue
        opts = dict(cfg.items(section))
        if opts.get('enabled', 'true').lower() in ('0', 'false', 'no', 'off'):
            continue
        cls = REGISTRY.get(opts.get('type', ''))
        if cls is None:
            logger.error('[%s] 未知的 type：%s', section, opts.get('type'))
            continue
        checks.append(cls(section.split(':', 1)[1], opts))
    return checks


def format_message(kind: str, check: Check, result: CheckResult) -> tuple[str, str]:
    host = get_setting('WATCHER', 'WATCHER_NAME', 'watcher')
    subject = f'{ICONS[result.status]} [{host}] {TITLES[kind]}：{check.name}（{result.status.name}）'
    return subject, result.message


class Watcher:
    def __init__(self, checks: list[Check], notifiers: list[Notifier]):
        self.checks = checks
        self.notifiers = notifiers
        self.interval = get_int('WATCHER', 'INTERVAL', 60)
        self.state = AlertState(_path('STATE_FILE', 'data/state.json'),
                                get_int('WATCHER', 'REMIND_INTERVAL', 1800))
        self.heartbeat_file = _path('HEARTBEAT_FILE', 'data/heartbeat')

    def run_once(self) -> dict[str, CheckResult]:
        results = {}
        for check in self.checks:
            result = check.safe_run()
            results[check.name] = result
            logger.log(logging.INFO if result.status == Status.OK else logging.WARNING,
                       '%s %s：%s', ICONS[result.status], check.name, result.message)
            kind = self.state.update(check.name, result)
            if kind:
                send_all(self.notifiers, *format_message(kind, check, result))
        self.state.save()
        beat(self.heartbeat_file)
        return results

    def run_forever(self) -> None:
        logger.info('Watcher 啟動：%d 個檢查，每 %d 秒', len(self.checks), self.interval)
        while True:
            started = time.monotonic()
            self.run_once()
            time.sleep(max(0.0, self.interval - (time.monotonic() - started)))
