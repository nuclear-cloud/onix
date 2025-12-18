import json
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
CODELIST_JSON_PATH = "/home/ubuntu/onix_project/data/ONIX_BookProduct_Codelists_Issue_71.json"

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def ingest():
    print(f"Loading ONIX Codelists from {CODELIST_JSON_PATH}...")
    with open(CODELIST_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    root = data.get("ONIXCodeTable", data)
    issue_number = root.get("IssueNumber")
    codelists = root.get("CodeList", [])
    print(f"Processing Issue {issue_number} with {len(codelists)} lists...")
    
    async with AsyncSessionLocal() as session:
        total_codes = 0
        for codelist in codelists:
            list_num = int(codelist.get("CodeListNumber"))
            list_name = codelist.get("CodeListDescription")
            
            # Upsert Codelist
            await session.execute(text("""
                INSERT INTO codelists (list_number, list_name, issue_number, is_active, updated_at)
                VALUES (:num, :name, :issue, TRUE, NOW())
                ON CONFLICT (list_number) DO UPDATE
                SET list_name = EXCLUDED.list_name,
                    issue_number = EXCLUDED.issue_number,
                    updated_at = NOW();
            """), {"num": list_num, "name": list_name, "issue": issue_number})
            
            codes = codelist.get("Code", [])
            for code in codes:
                val = code.get("CodeValue")
                desc = code.get("CodeDescription")
                notes = code.get("CodeNotes")
                
                await session.execute(text("""
                    INSERT INTO codelist_values (list_number, code_value, description, notes, is_active, updated_at)
                    VALUES (:num, :val, :desc, :notes, TRUE, NOW())
                    ON CONFLICT (list_number, code_value) DO UPDATE
                    SET description = EXCLUDED.description,
                        notes = EXCLUDED.notes,
                        updated_at = NOW();
                """), {"num": list_num, "val": val, "desc": desc, "notes": notes})
                total_codes += 1
            
            print(f"List {list_num}: {list_name} - {len(codes)} codes")
        
        await session.commit()
    print(f"Ingestion complete! Imported {total_codes} codes across {len(codelists)} lists.")

if __name__ == "__main__":
    asyncio.run(ingest())
