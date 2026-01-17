import asyncio
import json
from prisma import Prisma


async def main():
    db = Prisma()
    await db.connect()

    # Спробуємо зробити один UPSERT з усіма полями
    result = await db.query_raw(
        """
        INSERT INTO public.products 
        (id, source_name, external_id, sku, title, raw_data, content_hash, created_at, updated_at)
        VALUES (gen_random_uuid(), 'test_source', 'id_123', 'sku_123', 'Debug Title', '{}'::jsonb, 'hash_123', NOW(), NOW())
        ON CONFLICT (source_name, external_id) DO UPDATE SET updated_at = NOW()
        RETURNING id::text, title, (SELECT 100.5::float) as test_price;
        """
    )

    print(f"Result Type: {type(result)}")
    if result:
        row = result[0]
        print(f"Row Type: {type(row)}")
        print(f"Row Data: {row}")
        try:
            print(f"Access as dict: {row['id']}")
        except:
            print("FAILED to access as dict")

        try:
            print(f"Access as attr: {row.id}")
        except:
            print("FAILED to access as attr")

    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
