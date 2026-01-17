import asyncio
from redis.asyncio import Redis
import json

async def peek():
    r = Redis.from_url('redis://localhost:6379/0', decode_responses=True)
    item_json = await r.lindex('queue:vivat', 0)
    if item_json:
        item = json.loads(item_json)
        print(json.dumps(item["payload"], indent=2, ensure_ascii=False))
    else:
        print("Queue empty")
    await r.aclose()

asyncio.run(peek())
