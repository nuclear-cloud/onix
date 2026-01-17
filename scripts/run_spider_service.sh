#!/bin/bash
# Yakaboo Spider Service
# Runs the spider in an infinite loop to ensure continuous data freshness.
# - If finished (exit 0): Sleeps 1 hour, then restarts (from beginning).
# - If crashed (exit != 0): Sleeps 1 minute, then restarts (resumes).

LOG_FILE="spider_service.log"
SPIDER_CMD="./venv/bin/python scripts/yakaboo_spider.py"

echo "Starting Yakaboo Spider Service..." | tee -a "$LOG_FILE"

while true; do
    echo "----------------------------------------" | tee -a "$LOG_FILE"
    echo "Starting scan at $(date)" | tee -a "$LOG_FILE"
    
    # Run spider with resume flag
    # Note: If previous run finished successfully, state file was deleted by python script,
    # so --resume will just start from beginning, which is what we want.
    # If it crashed, state file exists, so --resume picks up where it left off.
    $SPIDER_CMD --resume >> "$LOG_FILE" 2>&1
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "Scan finished successfully at $(date)." | tee -a "$LOG_FILE"
        echo "Sleeping for 1 hour before next cycle..." | tee -a "$LOG_FILE"
        sleep 3600
    else
        echo "Spider crashed with exit code $EXIT_CODE at $(date)." | tee -a "$LOG_FILE"
        echo "Sleeping for 1 minute before RESUMING..." | tee -a "$LOG_FILE"
        sleep 60
    fi
done
