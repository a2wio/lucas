#!/bin/bash
set -e

echo "=== A2W Lucas Agent Starting ==="
echo "Target namespace: $TARGET_NAMESPACE"
echo "SQLite path: $SQLITE_PATH"

# === SRE MODE ===
SRE_MODE="${SRE_MODE:-autonomous}"
echo "Lucas agent mode: $SRE_MODE"

# === AUTHENTICATION SETUP ===
AUTH_MODE="${AUTH_MODE:-api-key}"
echo "Auth mode: $AUTH_MODE"

if [ "$AUTH_MODE" = "credentials" ]; then
    if [ -f "$HOME/.claude/.credentials.json" ]; then
        echo "Using mounted credentials.json"
    elif [ -f /secrets/credentials.json ]; then
        echo "Copying credentials from /secrets/"
        mkdir -p "$HOME/.claude"
        cp /secrets/credentials.json "$HOME/.claude/.credentials.json"
    else
        echo "ERROR: AUTH_MODE=credentials but no credentials.json found"
        exit 1
    fi
elif [ "$AUTH_MODE" = "api-key" ]; then
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo "ERROR: AUTH_MODE=api-key but ANTHROPIC_API_KEY not set"
        exit 1
    fi
    echo "Using API key authentication"
else
    echo "ERROR: Invalid AUTH_MODE: $AUTH_MODE (use 'api-key' or 'credentials')"
    exit 1
fi

# === DATABASE SETUP ===
# Ensure tables exist
sqlite3 "$SQLITE_PATH" "CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    namespace TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'autonomous',
    status TEXT NOT NULL DEFAULT 'running',
    pod_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    fix_count INTEGER DEFAULT 0,
    report TEXT,
    log TEXT
);"

sqlite3 "$SQLITE_PATH" "CREATE TABLE IF NOT EXISTS fixes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    timestamp TEXT NOT NULL,
    namespace TEXT NOT NULL,
    pod_name TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT,
    fix_applied TEXT,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (run_id) REFERENCES runs(id)
);"

# Add run_id column if missing (migration)
sqlite3 "$SQLITE_PATH" "ALTER TABLE fixes ADD COLUMN run_id INTEGER;" 2>/dev/null || true

echo "Database initialized"

# === CREATE RUN RECORD ===
RUN_ID=$(sqlite3 "$SQLITE_PATH" "INSERT INTO runs (started_at, namespace, mode, status) VALUES (datetime('now'), '$TARGET_NAMESPACE', '$SRE_MODE', 'running'); SELECT last_insert_rowid();")
echo "Created run #$RUN_ID"

# === GET LAST RUN TIME ===
LAST_RUN_TIME=$(sqlite3 "$SQLITE_PATH" "SELECT COALESCE(MAX(ended_at), '') FROM runs WHERE namespace = '$TARGET_NAMESPACE' AND status != 'running' AND id != $RUN_ID;")
echo "Last run time: ${LAST_RUN_TIME:-'(first run)'}"

# === SELECT PROMPT ===
if [ "$SRE_MODE" = "report" ]; then
    PROMPT_FILE="/app/master-prompt-report.md"
else
    PROMPT_FILE="/app/master-prompt-autonomous.md"
fi

if [ ! -f "$PROMPT_FILE" ]; then
    echo "ERROR: Prompt file not found: $PROMPT_FILE"
    sqlite3 "$SQLITE_PATH" "UPDATE runs SET ended_at = datetime('now'), status = 'failed', report = 'Prompt file not found' WHERE id = $RUN_ID;"
    exit 1
fi

PROMPT=$(cat "$PROMPT_FILE")

# Replace environment variables in prompt
PROMPT=$(echo "$PROMPT" | sed "s|\$TARGET_NAMESPACE|$TARGET_NAMESPACE|g")
PROMPT=$(echo "$PROMPT" | sed "s|\$SQLITE_PATH|$SQLITE_PATH|g")
PROMPT=$(echo "$PROMPT" | sed "s|\$RUN_ID|$RUN_ID|g")
PROMPT=$(echo "$PROMPT" | sed "s|\$LAST_RUN_TIME|$LAST_RUN_TIME|g")

# === RUN CLAUDE ===
echo "Starting Claude Code..."

LOG_FILE="/data/lucas.log"
echo "=== Run #$RUN_ID started at $(date -Iseconds) ===" > "$LOG_FILE"
echo "Mode: $SRE_MODE | Namespace: $TARGET_NAMESPACE" >> "$LOG_FILE"
echo "----------------------------------------" >> "$LOG_FILE"

# Capture output
OUTPUT_FILE="/tmp/claude_output_$RUN_ID.txt"
claude --dangerously-skip-permissions --verbose -p "$PROMPT" 2>&1 | tee -a "$LOG_FILE" | tee "$OUTPUT_FILE"

echo "=== Run #$RUN_ID Complete ===" | tee -a "$LOG_FILE"

# === PARSE REPORT ===
REPORT=""
if grep -q "===REPORT_START===" "$OUTPUT_FILE" 2>/dev/null; then
    REPORT=$(sed -n '/===REPORT_START===/,/===REPORT_END===/p' "$OUTPUT_FILE" | grep -v "===REPORT" | tr -d '\n' | tr -s ' ')
    echo "Parsed report: $REPORT"
fi

# Extract values from report with defaults
POD_COUNT=0
ERROR_COUNT=0
FIX_COUNT=0
STATUS="ok"

if [ -n "$REPORT" ]; then
    # Parse pod_count
    PARSED=$(echo "$REPORT" | grep -o '"pod_count"[[:space:]]*:[[:space:]]*[0-9]*' | grep -o '[0-9]*$')
    [ -n "$PARSED" ] && POD_COUNT=$PARSED

    # Parse error_count
    PARSED=$(echo "$REPORT" | grep -o '"error_count"[[:space:]]*:[[:space:]]*[0-9]*' | grep -o '[0-9]*$')
    [ -n "$PARSED" ] && ERROR_COUNT=$PARSED

    # Parse fix_count
    PARSED=$(echo "$REPORT" | grep -o '"fix_count"[[:space:]]*:[[:space:]]*[0-9]*' | grep -o '[0-9]*$')
    [ -n "$PARSED" ] && FIX_COUNT=$PARSED

    # Parse status
    PARSED=$(echo "$REPORT" | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')
    [ -n "$PARSED" ] && STATUS=$PARSED
fi

# Validate status is one of expected values
case "$STATUS" in
    ok|fixed|failed|issues_found|running) ;;
    *) STATUS="ok" ;;
esac

echo "Final values: pods=$POD_COUNT errors=$ERROR_COUNT fixes=$FIX_COUNT status=$STATUS"

# Read full log (limit size to prevent issues)
FULL_LOG=$(head -c 100000 "$LOG_FILE" | sed "s/'/''/g")

# Escape report for SQL
REPORT_ESCAPED=$(echo "$REPORT" | sed "s/'/''/g")

# === UPDATE RUN RECORD ===
sqlite3 "$SQLITE_PATH" "UPDATE runs SET
    ended_at = datetime('now'),
    status = '$STATUS',
    pod_count = $POD_COUNT,
    error_count = $ERROR_COUNT,
    fix_count = $FIX_COUNT,
    report = '$REPORT_ESCAPED',
    log = '$FULL_LOG'
WHERE id = $RUN_ID;"

echo "Run #$RUN_ID completed with status: $STATUS"

# === SLACK NOTIFICATION ===
if [ -n "$SLACK_WEBHOOK_URL" ]; then
    # Extract summary from report for Slack message
    SUMMARY=""
    if [ -n "$REPORT" ]; then
        SUMMARY=$(echo "$REPORT" | grep -o '"summary"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/' || echo "")
    fi

    # Call Slack notification script
    /app/slack-notify.sh "$STATUS" "$TARGET_NAMESPACE" "$RUN_ID" "$POD_COUNT" "$ERROR_COUNT" "$FIX_COUNT" "$SUMMARY" || echo "Slack notification failed (non-fatal)"
else
    echo "Slack notifications disabled (SLACK_WEBHOOK_URL not set)"
fi

# Cleanup
rm -f "$OUTPUT_FILE"
