import asyncio
from redis.asyncio import Redis


async def main():
    r = Redis.from_url("redis://localhost:6379/0")
    depth = await r.llen("queue:yakaboo")
    print(f"QUEUE_DEPTH:{depth}")
    await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
