#!/bin/bash

export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# Target directory
PROJECT_DIR="/Users/drop/breachblog"
cd "$PROJECT_DIR" || exit 1

LOCK_FILE="$PROJECT_DIR/.cron_running.lock"
if [ -f "$LOCK_FILE" ]; then
    # Check if lock file is stale (older than 2 hours / 120 minutes)
    if [ -n "$(find "$LOCK_FILE" -mmin +120 2>/dev/null)" ]; then
        echo "$(date): Stale lock file found (>2h old). Removing stale lock." >> "$PROJECT_DIR/cron_run.log"
        rm -f "$LOCK_FILE"
    else
        echo "$(date): Another instance is already running (lock file exists). Exiting." >> "$PROJECT_DIR/cron_run.log"
        exit 0
    fi
fi
touch "$LOCK_FILE"
trap "rm -f '$LOCK_FILE'" EXIT

# Check start delay
START_FILE="$PROJECT_DIR/.cron_start_time"

if [ ! -f "$START_FILE" ]; then
    # If the start time file doesn't exist, initialize it to the current time
    date +%s > "$START_FILE"
    echo "$(date): Cron script initialized. Waiting 24 hours to run the first publication." >> "$PROJECT_DIR/cron_run.log"
    exit 0
fi

START_TIME=$(cat "$START_FILE")
CURRENT_TIME=$(date +%s)

# Use 23 hours (82800 seconds) so that a 12-hour cron schedule running ~24h after previous run doesn't miss the window due to a few minutes of runtime drift
DELAY=82800
ELAPSED=$((CURRENT_TIME - START_TIME))

if [ "$ELAPSED" -lt "$DELAY" ]; then
    REMAINING=$((86400 - ELAPSED))
    if [ "$REMAINING" -lt 0 ]; then REMAINING=0; fi
    HOURS_REMAINING=$((REMAINING / 3600))
    MINS_REMAINING=$(( (REMAINING % 3600) / 60 ))
    echo "$(date): Delay active. ${HOURS_REMAINING}h ${MINS_REMAINING}m remaining before next run." >> "$PROJECT_DIR/cron_run.log"
    exit 0
fi

# Record start timestamp before execution so task duration does not drift the schedule
EXEC_START_TIME=$(date +%s)

# Run the python script
echo "$(date): Executing automated trending topic publication..." >> "$PROJECT_DIR/cron_run.log"
if ! command -v git-lfs &> /dev/null; then
    echo "$(date): Warning: git-lfs is not installed. Large file pushes may fail." >> "$PROJECT_DIR/cron_run.log"
fi

.venv/bin/python publish_trending.py >> "$PROJECT_DIR/cron_run.log" 2>&1
EXIT_CODE=$?
echo "$(date): Execution finished with exit code ${EXIT_CODE}." >> "$PROJECT_DIR/cron_run.log"

if [ "$EXIT_CODE" -eq 0 ]; then
    # Success: set start time to when execution began for the next 24 hour interval.
    echo "$EXEC_START_TIME" > "$START_FILE"
else
    # Failure: don't burn the whole window. Back the clock off so the next
    # cron tick (12h cadence) retries instead of waiting another full day.
    echo "$(date): Run failed. Will retry on the next cron tick." >> "$PROJECT_DIR/cron_run.log"
    echo $(( $(date +%s) - DELAY )) > "$START_FILE"
fi


