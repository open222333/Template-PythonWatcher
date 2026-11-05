from src.checks.base import Check, CheckResult, Status
from src.health import beat, is_healthy
from src.notify.base import Notifier
from src.watcher import Watcher


class Fixed(Check):
    def run(self):
        return CheckResult(Status(int(self.opts['status'])), 'fixed')


class Collect(Notifier):
    name = 'collect'

    def __init__(self):
        self.msgs = []

    def send(self, subject, body):
        self.msgs.append(subject)


def test_run_once_notifies_only_on_change(tmp_path, monkeypatch):
    monkeypatch.setenv('STATE_FILE', str(tmp_path / 'state.json'))
    monkeypatch.setenv('HEARTBEAT_FILE', str(tmp_path / 'hb'))
    n = Collect()
    chk = Fixed('svc', {'status': '2'})
    w = Watcher([chk], [n])
    w.run_once()
    w.run_once()
    assert len(n.msgs) == 1 and '告警' in n.msgs[0]
    chk.opts['status'] = '0'
    w.run_once()
    assert len(n.msgs) == 2 and '恢復' in n.msgs[1]
    assert is_healthy(str(tmp_path / 'hb'), 60)


def test_healthcheck_stale(tmp_path):
    hb = tmp_path / 'hb'
    assert is_healthy(str(hb), 60) is False
    beat(str(hb))
    assert is_healthy(str(hb), 60) is True
    hb.write_text('0')
    assert is_healthy(str(hb), 60) is False
