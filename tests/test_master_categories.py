import tempfile
import unittest
from pathlib import Path

from src import database as db


class MasterCategoriesTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db_path = db.DB_PATH
        db.DB_PATH = str(Path(self.tmp.name) / "test.sqlite3")
        await db.init_db()
        conn = await db.get_connection()
        try:
            await conn.execute(
                """
                INSERT INTO masters (id, tg_id, name, sphere, invite_token)
                VALUES (1, 1001, 'Анна', 'Клининг, Тату-мастер', 'invite_anna')
                """
            )
            await conn.commit()
        finally:
            await conn.close()

    async def asyncTearDown(self):
        db.DB_PATH = self.old_db_path
        self.tmp.cleanup()

    async def test_dictionary_seeded(self):
        categories = await db.get_all_categories()

        self.assertEqual(len(categories), 13)
        self.assertEqual(categories[0]["slug"], "cleaning")
        self.assertEqual(categories[-1]["slug"], "other")

    async def test_link_categories_from_sphere_maps_known_and_custom(self):
        await db.link_categories_from_sphere(1, "Клининг, Тату-мастер")

        categories = await db.get_master_categories(1)

        self.assertEqual([item["slug"] for item in categories], ["cleaning", "other"])
        self.assertIsNone(categories[0]["custom_name"])
        self.assertEqual(categories[1]["custom_name"], "Тату-мастер")

    async def test_set_master_categories_replaces_links_and_syncs_sphere(self):
        all_categories = await db.get_all_categories()
        by_slug = {item["slug"]: item for item in all_categories}

        await db.set_master_categories(
            1,
            [by_slug["barber"]["id"], by_slug["other"]["id"]],
            {by_slug["other"]["id"]: "Тату-мастер"},
        )

        categories = await db.get_master_categories(1)
        master = await db.get_master_by_id(1)

        self.assertEqual([item["slug"] for item in categories], ["barber", "other"])
        self.assertEqual(master.sphere, "Парикмахер и барбер, Тату-мастер")

    async def test_set_master_categories_rejects_unknown_ids(self):
        with self.assertRaises(ValueError):
            await db.set_master_categories(1, [9999])
