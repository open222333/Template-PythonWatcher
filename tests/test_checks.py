import configparser
import socket

from src.checks.base import Check, CheckResult, Status, evaluate
from src.checks.disk import DiskCheck
from src.checks.tcp import TcpCheck
from src.watcher import load_checks


def test_evaluate_thresholds():
    assert evaluate(50, 80, 90) == Status.OK
    assert evaluate(85, 80, 90) == Status.WARN
    assert evaluate(95, 80, 90) == Status.CRIT
    assert evaluate(95, None, None) == Status.OK


def test_disk_check_runs(tmp_path):
    res = DiskCheck('d', {'path': str(tmp_path), 'warn_percent': '101', 'crit_percent': '102'}).run()
    assert res.status == Status.OK and res.value is not None


def test_tcp_check_open_and_closed():
    srv = socket.socket()
    srv.bind(('127.0.0.1', 0))
    srv.listen()
    port = srv.getsockname()[1]
    assert TcpCheck('t', {'host': '127.0.0.1', 'port': str(port)}).run().status == Status.OK
    srv.close()
    assert TcpCheck('t', {'host': '127.0.0.1', 'port': str(port), 'timeout': '1'}).run().status == Status.CRIT


def test_safe_run_converts_exception():
    class Bad(Check):
        def run(self) -> CheckResult:
            raise ValueError('x')
    assert Bad('b', {}).safe_run().status == Status.UNKNOWN


def test_load_checks_skips_disabled_and_unknown():
    cfg = configparser.ConfigParser()
    cfg.read_string("""
[check:a]
type=disk
[check:b]
type=disk
enabled=false
[check:c]
type=nope
[OTHER]
x=1
""")
    assert [c.name for c in load_checks(cfg)] == ['a']
