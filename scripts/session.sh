#!/usr/bin/env bash
set -euo pipefail

DB=".claude/sessions.db"
mkdir -p "$(dirname "$DB")"

# Auto-detect session ID
if command -v tmux &>/dev/null && SID=$(tmux display-message -p '#{pane_id}' 2>/dev/null); then
    :
elif [[ -n "${PPID:-}" ]]; then
    SID="pid-$PPID"
else
    SID="pid-$$"
fi

init_db() {
    sqlite3 "$DB" "PRAGMA journal_mode=WAL;" &>/dev/null
    sqlite3 "$DB" "CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        domain TEXT,
        directory TEXT,
        status TEXT DEFAULT 'WORKING',
        description TEXT,
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    );"
}

case "${1:-help}" in
    register)
        init_db
        sqlite3 "$DB" "INSERT OR REPLACE INTO sessions (id, domain, directory, description, status, updated_at)
            VALUES ('$SID', '${2:-}', '${3:-}', '${4:-}', 'WORKING', datetime('now','localtime'));"
        echo "Registered session $SID"
        ;;
    check)
        init_db
        sqlite3 -header -column "$DB" "SELECT id, domain, directory, status, description, updated_at FROM sessions ORDER BY updated_at DESC;"
        ;;
    update)
        init_db
        sqlite3 "$DB" "UPDATE sessions SET status='${2:-WORKING}', updated_at=datetime('now','localtime') WHERE id='$SID';"
        echo "Updated session $SID → ${2:-WORKING}"
        ;;
    done)
        init_db
        sqlite3 "$DB" "DELETE FROM sessions WHERE id='$SID';"
        echo "Removed session $SID"
        ;;
    cleanup)
        init_db
        echo "Stale sessions (>1 day old):"
        sqlite3 -header -column "$DB" "SELECT * FROM sessions WHERE updated_at < datetime('now','localtime','-1 day');"
        sqlite3 "$DB" "DELETE FROM sessions WHERE updated_at < datetime('now','localtime','-1 day');"
        echo "Cleaned up."
        ;;
    help|*)
        echo "Usage: scripts/session.sh <command> [args]"
        echo "  register <domain> <directory> <description>  — claim work area"
        echo "  check                                        — show all sessions"
        echo "  update <STATUS>                              — update own status"
        echo "  done                                         — remove own entry"
        echo "  cleanup                                      — remove entries >1 day old"
        ;;
esac
