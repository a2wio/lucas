#!/bin/bash
set -e

echo "=== Clopus Watcher Starting ==="
echo "Target namespace: $TARGET_NAMESPACE"
echo "SQLite path: $SQLITE_PATH"

# === AUTHENTICATION SETUP ===
# Supports two modes via AUTH_MODE env var:
#   - "api-key" (default): Uses ANTHROPIC_API_KEY env var
#   - "credentials": Uses mounted credentials.json file

AUTH_MODE="${AUTH_MODE:-api-key}"
echo "Auth mode: $AUTH_MODE"

if [ "$AUTH_MODE" = "credentials" ]; then
    # Check for mounted credentials file
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
    # Check for API key
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
sqlite3 "$SQLITE_PATH" "CREATE TABLE IF NOT EXISTS fixes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    namespace TEXT NOT NULL,
    pod_name TEXT NOT NULL,
    error_type TEXT NOT NULL,
    error_message TEXT,
    fix_applied TEXT,
    status TEXT DEFAULT 'pending'
);"
echo "Database initialized"

# === LOAD PROMPT ===
if [ -f /config/master-prompt.md ]; then
    PROMPT=$(cat /config/master-prompt.md)
elif [ -f /app/master-prompt.md ]; then
    PROMPT=$(cat /app/master-prompt.md)
else
    echo "ERROR: No master prompt found"
    exit 1
fi

# Replace environment variables in prompt
PROMPT=$(echo "$PROMPT" | sed "s|\$TARGET_NAMESPACE|$TARGET_NAMESPACE|g")
PROMPT=$(echo "$PROMPT" | sed "s|\$SQLITE_PATH|$SQLITE_PATH|g")

# === RUN CLAUDE ===
echo "Starting Claude Code..."
claude --dangerously-skip-permissions -p "$PROMPT"

echo "=== Clopus Watcher Complete ==="
