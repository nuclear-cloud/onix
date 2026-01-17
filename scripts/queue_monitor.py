#!/usr/bin/env python3
"""
Redis Queue Monitor & DLQ Manager.

Usage:
    python scripts/queue_monitor.py status           # Show queue stats
    python scripts/queue_monitor.py dlq-list         # List DLQ contents
    python scripts/queue_monitor.py dlq-retry        # Retry all DLQ tasks
    python scripts/queue_monitor.py dlq-purge        # Purge DLQ
    python scripts/queue_monitor.py recover          # Recover orphaned tasks
"""
import asyncio
import argparse
import json
import os
from datetime import datetime
from redis.asyncio import Redis

REDIS_URL = os.getenv("REDIS_PROD_URL", "redis://localhost:6379/0")
SOURCE = "yakaboo"

async def get_redis():
    return Redis.from_url(REDIS_URL, decode_responses=True)


async def show_status():
    """Show current queue statistics."""
    r = await get_redis()
    
    queue_name = f"queue:{SOURCE}"
    processing = f"queue:{SOURCE}:processing"
    dlq = f"queue:{SOURCE}:dlq"
    
    stats = {
        "Queue (pending)": await r.llen(queue_name),
        "Processing": await r.llen(processing),
        "DLQ (failed)": await r.llen(dlq),
    }
    
    # Count active locks
    lock_keys = []
    async for key in r.scan_iter(f"lock:{SOURCE}:*"):
        lock_keys.append(key)
    stats["Active Locks"] = len(lock_keys)
    
    print("\n" + "=" * 50)
    print(f"📊 QUEUE STATUS [{SOURCE}] - {datetime.now().isoformat()}")
    print("=" * 50)
    for name, value in stats.items():
        status = "🔴" if "DLQ" in name and value > 0 else "🟢"
        print(f"  {status} {name}: {value:,}")
    print("=" * 50 + "\n")
    
    await r.aclose()


async def list_dlq():
    """List contents of Dead Letter Queue."""
    r = await get_redis()
    dlq = f"queue:{SOURCE}:dlq"
    
    tasks = await r.lrange(dlq, 0, 50)  # First 50
    total = await r.llen(dlq)
    
    print(f"\n📋 DLQ CONTENTS ({len(tasks)} of {total} shown)\n")
    
    for i, task_json in enumerate(tasks, 1):
        try:
            task = json.loads(task_json)
            error = task.get("_dlq_error", "Unknown")[:80]
            timestamp = task.get("_dlq_timestamp", "Unknown")
            ext_id = task.get("payload", {}).get("id", "?")
            print(f"  {i}. ID: {ext_id}")
            print(f"     Error: {error}")
            print(f"     Time: {timestamp}")
            print()
        except Exception as e:
            print(f"  {i}. [Invalid JSON]: {e}")
    
    await r.aclose()


async def retry_dlq():
    """Move all DLQ tasks back to main queue for retry."""
    r = await get_redis()
    
    queue_name = f"queue:{SOURCE}"
    dlq = f"queue:{SOURCE}:dlq"
    
    count = 0
    while True:
        task = await r.rpoplpush(dlq, queue_name)
        if not task:
            break
        # Reset retry counter
        try:
            task_dict = json.loads(task)
            task_dict.pop("_retry_count", None)
            task_dict.pop("_dlq_error", None)
            task_dict.pop("_dlq_timestamp", None)
            task_dict.pop("_last_error", None)
            await r.lrem(queue_name, 1, task)
            await r.lpush(queue_name, json.dumps(task_dict))
        except Exception:
            pass
        count += 1
    
    print(f"✅ Moved {count} tasks from DLQ back to queue")
    await r.aclose()


async def purge_dlq():
    """Delete all tasks in DLQ."""
    r = await get_redis()
    dlq = f"queue:{SOURCE}:dlq"
    
    count = await r.llen(dlq)
    await r.delete(dlq)
    
    print(f"🗑️  Purged {count} tasks from DLQ")
    await r.aclose()


async def recover_orphaned():
    """Move orphaned processing tasks back to main queue."""
    r = await get_redis()
    
    queue_name = f"queue:{SOURCE}"
    processing = f"queue:{SOURCE}:processing"
    
    count = 0
    while True:
        task = await r.rpoplpush(processing, queue_name)
        if not task:
            break
        count += 1
    
    print(f"🔄 Recovered {count} orphaned tasks from processing queue")
    await r.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Queue Monitor & DLQ Manager")
    parser.add_argument("command", choices=["status", "dlq-list", "dlq-retry", "dlq-purge", "recover"])
    parser.add_argument("--source", default="yakaboo", help="Source name")
    args = parser.parse_args()
    
    SOURCE = args.source
    
    commands = {
        "status": show_status,
        "dlq-list": list_dlq,
        "dlq-retry": retry_dlq,
        "dlq-purge": purge_dlq,
        "recover": recover_orphaned,
    }
    
    asyncio.run(commands[args.command]())
