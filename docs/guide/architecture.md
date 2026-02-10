# Architecture

## Components

- **Agent (Slack)**: long-running service that answers Slack mentions and runs scheduled scans.
- **Agent (CronJob)**: batch worker that runs on a schedule and writes a report.
- **Dashboard**: web UI for runs, sessions, fixes, and token usage.
- **SQLite**: shared database for runs, fixes, sessions, and token usage.
- **PVCs**: persistent storage for `lucas.db`, logs, and Claude sessions.

## Data flow

1. A Slack mention or a scheduled scan triggers the agent.
2. The agent runs Claude Code with kubectl access.
3. Findings are written to SQLite.
4. The dashboard reads from SQLite.

## Scheduled scans

The interactive agent includes a scheduler. It scans namespaces from `TARGET_NAMESPACES` every `SCAN_INTERVAL_SECONDS` and posts results to `SRE_ALERT_CHANNEL`.

## Master prompts

Lucas behavior is driven by master prompt files included in the agent image. The selected prompt depends on mode:

- Interactive agent: `master-prompt-interactive.md` (autonomous) or `master-prompt-interactive-report.md` (watcher).
- CronJob: `master-prompt-autonomous.md` or `master-prompt-report.md`.

The prompt defines the rules of engagement, required output format, and runbook usage. Variables like `$TARGET_NAMESPACE`, `$SQLITE_PATH`, `$RUN_ID`, and `$LAST_RUN_TIME` are replaced at runtime.
