"""One-time migration from masters.sphere to master_category_links.

Run:
    python scripts/migrate_categories.py

The script is safe to run repeatedly. Existing links are preserved because it
uses INSERT OR IGNORE.
"""

import asyncio
import sys
from pathlib import Path

import aiosqlite

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import DB_PATH


async def migrate() -> None:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")

    cursor = await conn.execute("SELECT id, name, slug FROM master_categories WHERE is_active = 1")
    category_rows = await cursor.fetchall()
    categories_by_name = {row["name"]: row["id"] for row in category_rows}
    other_id = next((row["id"] for row in category_rows if row["slug"] == "other"), None)
    if other_id is None:
        raise RuntimeError("Category 'other' is missing")

    cursor = await conn.execute("SELECT id, sphere FROM masters WHERE sphere IS NOT NULL AND sphere != ''")
    masters = await cursor.fetchall()

    total_links = 0
    total_other = 0

    for master in masters:
        parts = [part.strip() for part in master["sphere"].split(",") if part.strip()]
        used_category_ids: set[int] = set()

        for index, part in enumerate(parts[:3]):
            category_id = categories_by_name.get(part)
            custom_name = None
            if category_id is None:
                category_id = other_id
                if category_id in used_category_ids:
                    continue
                custom_name = part[:100]
                total_other += 1

            if category_id in used_category_ids:
                continue
            used_category_ids.add(category_id)

            cursor = await conn.execute(
                """
                INSERT OR IGNORE INTO master_category_links
                    (master_id, category_id, custom_name, sort_order)
                VALUES (?, ?, ?, ?)
                """,
                (master["id"], category_id, custom_name, index),
            )
            total_links += cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0

    await conn.commit()
    await conn.close()

    print(f"Done: {len(masters)} masters, {total_links} links, {total_other} custom->other")


if __name__ == "__main__":
    asyncio.run(migrate())
