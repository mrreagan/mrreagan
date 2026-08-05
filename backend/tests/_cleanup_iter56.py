"""One-off cleanup of TEST_iter56 comments created during testing."""
import asyncio
import os
import sys

sys.path.insert(0, "/app/backend")
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import dotenv_values

env = dotenv_values("/app/backend/.env")


async def main():
    client = AsyncIOMotorClient(env["MONGO_URL"])
    db = client[env["DB_NAME"]]
    names = await db.list_collection_names()
    total = 0
    for name in names:
        if "comment" in name or "ratification" in name:
            res = await db[name].delete_many({"$or": [
                {"body": {"$regex": "TEST_iter56"}},
                {"notes": {"$regex": "TEST_iter56"}},
                {"comment": {"$regex": "TEST_iter56"}},
            ]})
            if res.deleted_count:
                print(name, "deleted", res.deleted_count)
                total += res.deleted_count
    print("total deleted", total)


asyncio.run(main())
