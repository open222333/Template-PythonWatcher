from src.checks.base import CheckResult, Status
from src.state import AlertState


def r(status):
    return CheckResult(status, 'msg')


def test_first_ok_no_notify(tmp_path):
    s = AlertState(str(tmp_path / 's.json'))
    assert s.update('a', r(Status.OK), now=0) is None


def test_alert_dedup_remind_recovery(tmp_path):
    s = AlertState(str(tmp_path / 's.json'), remind_interval=100)
    assert s.update('a', r(Status.OK), now=0) is None
    assert s.update('a', r(Status.CRIT), now=10) == 'alert'
    assert s.update('a', r(Status.CRIT), now=50) is None          # 去重
    assert s.update('a', r(Status.CRIT), now=111) == 'remind'     # 超過提醒間隔
    assert s.update('a', r(Status.CRIT), now=150) is None
    assert s.update('a', r(Status.WARN), now=160) == 'alert'      # 嚴重度改變
    assert s.update('a', r(Status.OK), now=170) == 'recovery'
    assert s.update('a', r(Status.OK), now=999) is None


def test_state_persists(tmp_path):
    p = str(tmp_path / 's.json')
    s = AlertState(p)
    s.update('a', r(Status.CRIT), now=0)
    s.save()
    s2 = AlertState(p)
    assert s2.update('a', r(Status.CRIT), now=1) is None


def test_corrupt_state_file_ignored(tmp_path):
    p = tmp_path / 's.json'
    p.write_text('{broken')
    assert AlertState(str(p)).entries == {}
