#!/bin/bash
# Vivat Spider Service
# Runs the spider in an infinite loop.
# - If finished (exit 0): Sleeps 1 hour, then restarts.
# - If crashed (exit != 0): Sleeps 1 minute, then resumes.

LOG_FILE="vivat_service.log"
SPIDER_CMD="./venv/bin/python scripts/vivat_spider.py"

echo "Starting Vivat Spider Service..." | tee -a "$LOG_FILE"

while true; do
    echo "----------------------------------------" | tee -a "$LOG_FILE"
    echo "Starting scan at $(date)" | tee -a "$LOG_FILE"
    
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
