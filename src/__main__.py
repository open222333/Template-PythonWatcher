"""程式進入點。

python -m src               持續監控
python -m src --once        執行一輪後結束（適合 cron）
python -m src healthcheck   檢查 heartbeat（Docker HEALTHCHECK 使用）
"""
import argparse
import logging
import sys

from src import get_int
from src.health import is_healthy
from src.log import setup_logging
from src.notify import build_notifiers
from src.watcher import Watcher, _path, load_checks

logger = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog='python -m src')
    parser.add_argument('command', nargs='?', choices=['run', 'healthcheck'], default='run')
    parser.add_argument('--once', action='store_true', help='只執行一輪')
    args = parser.parse_args(argv)

    if args.command == 'healthcheck':
        max_age = get_int('WATCHER', 'INTERVAL', 60) * 3
        return 0 if is_healthy(_path('HEARTBEAT_FILE', 'data/heartbeat'), max_age) else 1

    setup_logging()
    checks = load_checks()
    if not checks:
        logger.error('沒有任何檢查項目，請在 conf/config.ini 新增 [check:<name>] 區段')
        return 2
    watcher = Watcher(checks, build_notifiers())
    if args.once:
        results = watcher.run_once()
        return 0 if all(r.status == 0 for r in results.values()) else 1
    try:
        watcher.run_forever()
    except KeyboardInterrupt:
        logger.info('Watcher 停止')
    return 0


if __name__ == '__main__':
    sys.exit(main())
