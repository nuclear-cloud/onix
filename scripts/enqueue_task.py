#!/usr/bin/env python3
import json
import asyncio
import argparse
from redis.asyncio import Redis


async def enqueue(source: str, file_path: str, redis_url: str):
    redis = Redis.from_url(redis_url, decode_responses=True)
    queue_name = f"queue:{source}"

    task = {
        "type": "file_bulk",
        "source": source,
        "target": file_path,
        "priority": "high",
    }

    await redis.lpush(queue_name, json.dumps(task))
    print(f"✅ Enqueued bulk task for {source} into {queue_name}")
    print(f"Target file: {file_path}")

    await redis.aclose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="yakaboo", help="Source name")
    parser.add_argument("--file", required=True, help="Path to JSONL file")
    parser.add_argument("--redis", default="redis://localhost:6379/0", help="Redis URL")

    args = parser.parse_args()
    asyncio.run(enqueue(args.source, args.file, args.redis))
