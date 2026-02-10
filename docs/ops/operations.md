# Operations

## Scheduled scans

The interactive agent can scan multiple namespaces on a timer.

Set:

- `TARGET_NAMESPACES` (comma-separated)
- `SCAN_INTERVAL_SECONDS`
- `SRE_ALERT_CHANNEL`

If `SRE_ALERT_CHANNEL` is empty, scheduled scans are disabled.

## Storage and data

- SQLite lives at `SQLITE_PATH` (default `/data/lucas.db`).
- The CronJob and dashboard share the same PVC (`lucas-data`).
- Slack sessions are stored in SQLite and cleaned after 7 days.

## Logs

- CronJob runs write to `/data/lucas.log`.
- The dashboard reads from `LOG_PATH`.
- The agent logs are available via `kubectl logs`.
