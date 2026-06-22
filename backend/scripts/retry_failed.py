"""Retry every 'failed' queue entry by resetting status → queued and
running the bulk generator. Useful after a budget top-up."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import db  # noqa: E402


async def main():
    res = await db.pending_additional_images.update_many(
        {"status": "failed"},
        {"$set": {"status": "queued", "error": None}},
    )
    print(f"Reset {res.modified_count} failed entries to queued.")


if __name__ == "__main__":
    asyncio.run(main())
