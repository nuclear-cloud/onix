#!/bin/bash
# ETL Progress Monitor
echo "=== ETL Import Progress ==="
echo "Date: $(date)"
echo ""

# Check if process is running
PID=$(pgrep -f "etl_yakaboo.py" 2>/dev/null | head -1)
if [ -n "$PID" ]; then
    echo "Status: RUNNING ✓"
    echo "PID: $PID"
else
    echo "Status: NOT RUNNING"
fi

echo ""

# Database stats
echo "Database records:"
PGPASSWORD=onix_secure_pass_2024 psql -h localhost -U onix_user -d onix_db -t << 'SQL' 2>/dev/null
SELECT 
    '  Total:   ' || COUNT(*)::text
    || E'\n  NEW:     ' || COUNT(*) FILTER (WHERE status = 'NEW')::text
    || E'\n  NOCODE:  ' || COUNT(*) FILTER (WHERE status = 'NOCODE')::text
    || E'\n  BOOK_UA: ' || COUNT(*) FILTER (WHERE item_type = 'BOOK_UA')::text
    || E'\n  BOOK_EN: ' || COUNT(*) FILTER (WHERE item_type = 'BOOK_EN')::text
    || E'\n  BOOK_RU: ' || COUNT(*) FILTER (WHERE item_type = 'BOOK_RU')::text
FROM cold."RawIngestion";
SQL

echo ""
echo "Progress from log:"
tail -5 /home/ubuntu/onix_project/logs/etl_import.log 2>/dev/null | grep "Progress" || echo "(checking...)"
