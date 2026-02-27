"""Async database layer for Master CRM Bot."""

import aiosqlite
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.models import Master, Client, MasterClient
from src.config import DATABASE_URL

# Extract database path from URL
DB_PATH = DATABASE_URL.replace("sqlite:///", "") if DATABASE_URL.startswith("sqlite:///") else "db.sqlite3"
MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"


async def get_connection() -> aiosqlite.Connection:
    """Get a database connection."""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    return conn


async def init_db() -> None:
    """Initialize database by running migrations."""
    conn = await get_connection()
    try:
        # Read and execute migration file
        migration_file = MIGRATIONS_DIR / "001_init.sql"
        if migration_file.exists():
            sql = migration_file.read_text()
            await conn.executescript(sql)
            await conn.commit()
    finally:
        await conn.close()


# =============================================================================
# Masters CRUD
# =============================================================================

async def get_master_by_tg_id(tg_id: int) -> Optional[Master]:
    """Get master by Telegram ID."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM masters WHERE tg_id = ?",
            (tg_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Master(
                id=row["id"],
                tg_id=row["tg_id"],
                name=row["name"],
                sphere=row["sphere"],
                socials=row["socials"],
                contacts=row["contacts"],
                work_hours=row["work_hours"],
                invite_token=row["invite_token"],
                bonus_enabled=bool(row["bonus_enabled"]),
                bonus_rate=row["bonus_rate"],
                bonus_max_spend=row["bonus_max_spend"],
                bonus_birthday=row["bonus_birthday"],
                gc_connected=bool(row["gc_connected"]),
                gc_credentials=row["gc_credentials"],
                created_at=row["created_at"],
            )
        return None
    finally:
        await conn.close()


async def get_master_by_invite_token(invite_token: str) -> Optional[Master]:
    """Get master by invite token."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM masters WHERE invite_token = ?",
            (invite_token,)
        )
        row = await cursor.fetchone()
        if row:
            return Master(
                id=row["id"],
                tg_id=row["tg_id"],
                name=row["name"],
                sphere=row["sphere"],
                socials=row["socials"],
                contacts=row["contacts"],
                work_hours=row["work_hours"],
                invite_token=row["invite_token"],
                bonus_enabled=bool(row["bonus_enabled"]),
                bonus_rate=row["bonus_rate"],
                bonus_max_spend=row["bonus_max_spend"],
                bonus_birthday=row["bonus_birthday"],
                gc_connected=bool(row["gc_connected"]),
                gc_credentials=row["gc_credentials"],
                created_at=row["created_at"],
            )
        return None
    finally:
        await conn.close()


async def create_master(
    tg_id: int,
    name: str,
    invite_token: str,
    sphere: Optional[str] = None,
    contacts: Optional[str] = None,
    socials: Optional[str] = None,
    work_hours: Optional[str] = None,
) -> Master:
    """Create a new master."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO masters (tg_id, name, invite_token, sphere, contacts, socials, work_hours)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (tg_id, name, invite_token, sphere, contacts, socials, work_hours)
        )
        await conn.commit()
        master_id = cursor.lastrowid

        return Master(
            id=master_id,
            tg_id=tg_id,
            name=name,
            invite_token=invite_token,
            sphere=sphere,
            contacts=contacts,
            socials=socials,
            work_hours=work_hours,
        )
    finally:
        await conn.close()


async def update_master(master_id: int, **kwargs) -> None:
    """Update master fields."""
    if not kwargs:
        return

    conn = await get_connection()
    try:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [master_id]

        await conn.execute(
            f"UPDATE masters SET {set_clause} WHERE id = ?",
            values
        )
        await conn.commit()
    finally:
        await conn.close()


# =============================================================================
# Clients CRUD
# =============================================================================

async def get_client_by_tg_id(tg_id: int) -> Optional[Client]:
    """Get client by Telegram ID."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM clients WHERE tg_id = ?",
            (tg_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Client(
                id=row["id"],
                tg_id=row["tg_id"],
                name=row["name"],
                phone=row["phone"],
                birthday=row["birthday"],
                registered_via=row["registered_via"],
                created_at=row["created_at"],
            )
        return None
    finally:
        await conn.close()


async def get_client_by_phone(phone: str) -> Optional[Client]:
    """Get client by phone number."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM clients WHERE phone = ?",
            (phone,)
        )
        row = await cursor.fetchone()
        if row:
            return Client(
                id=row["id"],
                tg_id=row["tg_id"],
                name=row["name"],
                phone=row["phone"],
                birthday=row["birthday"],
                registered_via=row["registered_via"],
                created_at=row["created_at"],
            )
        return None
    finally:
        await conn.close()


async def create_client(
    name: str,
    tg_id: Optional[int] = None,
    phone: Optional[str] = None,
    birthday: Optional[str] = None,
    registered_via: Optional[int] = None,
) -> Client:
    """Create a new client."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO clients (tg_id, name, phone, birthday, registered_via)
            VALUES (?, ?, ?, ?, ?)
            """,
            (tg_id, name, phone, birthday, registered_via)
        )
        await conn.commit()
        client_id = cursor.lastrowid

        return Client(
            id=client_id,
            tg_id=tg_id,
            name=name,
            phone=phone,
            birthday=birthday,
            registered_via=registered_via,
        )
    finally:
        await conn.close()


async def update_client(client_id: int, **kwargs) -> None:
    """Update client fields."""
    if not kwargs:
        return

    conn = await get_connection()
    try:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [client_id]

        await conn.execute(
            f"UPDATE clients SET {set_clause} WHERE id = ?",
            values
        )
        await conn.commit()
    finally:
        await conn.close()


async def link_client_to_master(master_id: int, client_id: int) -> MasterClient:
    """Create master-client relationship."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO master_clients (master_id, client_id)
            VALUES (?, ?)
            ON CONFLICT(master_id, client_id) DO NOTHING
            """,
            (master_id, client_id)
        )
        await conn.commit()

        # Get the created or existing record
        cursor = await conn.execute(
            "SELECT * FROM master_clients WHERE master_id = ? AND client_id = ?",
            (master_id, client_id)
        )
        row = await cursor.fetchone()

        return MasterClient(
            id=row["id"],
            master_id=row["master_id"],
            client_id=row["client_id"],
            bonus_balance=row["bonus_balance"],
            total_spent=row["total_spent"],
            note=row["note"],
            first_visit=row["first_visit"],
            last_visit=row["last_visit"],
            notify_reminders=bool(row["notify_reminders"]),
            notify_marketing=bool(row["notify_marketing"]),
        )
    finally:
        await conn.close()


async def get_master_client(master_id: int, client_id: int) -> Optional[MasterClient]:
    """Get master-client relationship."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM master_clients WHERE master_id = ? AND client_id = ?",
            (master_id, client_id)
        )
        row = await cursor.fetchone()
        if row:
            return MasterClient(
                id=row["id"],
                master_id=row["master_id"],
                client_id=row["client_id"],
                bonus_balance=row["bonus_balance"],
                total_spent=row["total_spent"],
                note=row["note"],
                first_visit=row["first_visit"],
                last_visit=row["last_visit"],
                notify_reminders=bool(row["notify_reminders"]),
                notify_marketing=bool(row["notify_marketing"]),
            )
        return None
    finally:
        await conn.close()


async def get_today_orders_for_master(master_id: int) -> list[dict]:
    """Get today's orders for a master."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT o.*, c.name as client_name
            FROM orders o
            JOIN clients c ON o.client_id = c.id
            WHERE o.master_id = ?
              AND date(o.scheduled_at) = date('now')
              AND o.status IN ('new', 'confirmed')
            ORDER BY o.scheduled_at
            """,
            (master_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()
