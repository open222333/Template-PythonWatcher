# Template-PythonWatcher

```
Python 監控 + 通知模板
定時檢查迴圈、門檻設定、Telegram / Mail 通知、狀態去重（不重複發告警）、healthcheck
```

## 目錄

- [目錄結構](#目錄結構)
- [基於此模板建立新專案](#基於此模板建立新專案)
- [設定](#設定)
- [檢查項目](#檢查項目)
- [告警去重規則](#告警去重規則)
- [本機執行](#本機執行)
- [Docker](#docker)
- [新增檢查類型](#新增檢查類型)
- [新增通知管道](#新增通知管道)

## 目錄結構

```
Template-PythonWatcher/
├── conf/
│   └── config.ini.default   # 設定 + 檢查項目範本（複製為 config.ini）
├── docker/
│   └── Dockerfile           # python:3.13-slim，非 root 執行
├── src/
│   ├── __init__.py          # 讀取設定（get_setting / get_int / get_bool）
│   ├── __main__.py          # 進入點：run / --once / healthcheck
│   ├── log.py               # logging（console + logs/app.log 輪替）
│   ├── watcher.py           # 檢查迴圈、載入 [check:*]、組通知訊息
│   ├── state.py             # 告警狀態與去重（data/state.json，原子寫入）
│   ├── health.py            # heartbeat
│   ├── checks/              # http / tcp / disk，可自行擴充
│   └── notify/              # console / telegram / mail
├── tests/
├── .env.default             # 機密（TELEGRAM_BOT_TOKEN、SMTP_PASSWORD）
├── docker-compose.yml
├── requirements.txt
├── requirements-test.txt
└── pytest.ini
```

## 基於此模板建立新專案

```bash
git clone <此模板 URL> your-new-project
cd your-new-project
rm -rf .git && git init          # 不保留模板歷史
cp conf/config.ini.default conf/config.ini
cp .env.default .env
```

## 設定

讀取順序：**環境變數 > `conf/config.ini` > 預設值**。

| 區段 / 鍵 | 說明 | 預設 |
|---|---|---|
| `[WATCHER] WATCHER_NAME` | 通知標題中的名稱 | `watcher` |
| `[WATCHER] INTERVAL` | 檢查間隔（秒） | `60` |
| `[WATCHER] REMIND_INTERVAL` | 持續異常時重複提醒間隔（秒） | `1800` |
| `[WATCHER] STATE_FILE` / `HEARTBEAT_FILE` | 狀態檔 / heartbeat 路徑 | `data/state.json` / `data/heartbeat` |
| `[NOTIFY] NOTIFY_CHANNELS` | `console,telegram,mail` | `console` |
| `[TELEGRAM] TELEGRAM_CHAT_ID` | 接收的 chat id | — |
| `TELEGRAM_BOT_TOKEN`（env） | Bot Token，**只放 `.env`** | — |
| `[MAIL] SMTP_*` / `MAIL_FROM` / `MAIL_TO` | SMTP 設定 | — |
| `SMTP_PASSWORD`（env） | SMTP 密碼，**只放 `.env`** | — |

- 設定不完整的通知管道會自動略過並記 warning
- 單一管道發送失敗不影響其他管道與監控迴圈

## 檢查項目

每個 `[check:<名稱>]` 區段是一個檢查，`enabled=false` 可暫停：

| type | 參數 | 判斷 |
|---|---|---|
| `http` | `url`、`expect_status`(200)、`timeout`(10)、`warn_ms`、`crit_ms` | 狀態碼不符或連線失敗 → CRIT；回應時間超過門檻 → WARN / CRIT |
| `tcp` | `host`、`port`、`timeout`(5) | 無法連線 → CRIT |
| `disk` | `path`(/)、`warn_percent`(80)、`crit_percent`(90) | 使用率超過門檻 → WARN / CRIT |

```ini
[check:api]
type=http
url=https://api.example.com/health
warn_ms=800
crit_ms=2000
```

狀態：`OK` / `WARN` / `CRIT` / `UNKNOWN`（檢查本身拋出例外）。

## 告警去重規則

| 情況 | 通知 |
|---|---|
| 狀態改變為異常（OK→WARN、WARN→CRIT…） | 🔴 告警 |
| 異常 → OK | ✅ 恢復 |
| 持續相同異常，距上次通知 ≥ `REMIND_INTERVAL` | 持續異常提醒 |
| 持續相同狀態（未達提醒間隔） / 持續 OK | 不通知 |

狀態保存在 `data/state.json`，重啟後不會重複發送已發過的告警。

## 本機執行

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-test.txt
python -m src                # 持續監控
python -m src --once         # 只跑一輪（全部 OK 時 exit 0，否則 1；適合 cron）
python -m src healthcheck    # heartbeat 在 3 × INTERVAL 內 → exit 0
pytest
```

cron 範例（不常駐，每 5 分鐘一輪）：

```cron
*/5 * * * * cd /opt/your-watcher && .venv/bin/python -m src --once >> logs/cron.log 2>&1
```

## Docker

```bash
docker compose up -d --build
docker compose ps                  # STATUS 顯示 healthy / unhealthy
docker compose logs -f watcher
```

- `conf/` 唯讀掛載，`data/`（狀態檔）與 `logs/` 持久化
- 監控主機磁碟：在 compose 取消註解 `- /:/host:ro`，並將 `[check:root_disk] path` 改為 `/host`

## 新增檢查類型

1. 在 `src/checks/` 新增類別，繼承 `Check` 並實作 `run()` 回傳 `CheckResult`
2. 加入 `src/checks/__init__.py` 的 `REGISTRY`

```python
from src.checks.base import Check, CheckResult, evaluate


class QueueLengthCheck(Check):
    def run(self) -> CheckResult:
        length = get_queue_length(self.opts['queue'])   # 自行實作
        status = evaluate(length, self.opt_float('warn'), self.opt_float('crit'))
        return CheckResult(status, f'{self.opts["queue"]} 長度 {length}', length)
```

```ini
[check:jobs]
type=queue
queue=default
warn=100
crit=1000
```

## 新增通知管道

在 `src/notify/` 繼承 `Notifier`，實作 `enabled()` 與 `send(subject, body)`，再加入 `src/notify/__init__.py` 的 `_REGISTRY`。
