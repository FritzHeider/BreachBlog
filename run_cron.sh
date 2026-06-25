#!/bin/bash

# Target directory
PROJECT_DIR="/Users/drop/breachblog"
cd "$PROJECT_DIR" || exit 1

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
# 24 hours is 86400 seconds
DELAY=86400
ELAPSED=$((CURRENT_TIME - START_TIME))

if [ "$ELAPSED" -lt "$DELAY" ]; then
    REMAINING=$((DELAY - ELAPSED))
    echo "$(date): Delay active. $((REMAINING / 3600)) hours remaining before first run." >> "$PROJECT_DIR/cron_run.log"
    exit 0
fi

# Run the python script
echo "$(date): Executing automated trending topic publication..." >> "$PROJECT_DIR/cron_run.log"
.venv/bin/python publish_trending.py >> "$PROJECT_DIR/cron_run.log" 2>&1
echo "$(date): Execution finished with exit code $?." >> "$PROJECT_DIR/cron_run.log"

# Update start time for the next 24 hour interval
date +%s > "$START_FILE"

