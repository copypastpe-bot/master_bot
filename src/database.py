"""Async database layer for Master CRM Bot."""

import calendar
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import aiosqlite
from dateutil.relativedelta import relativedelta

from src.models import Master, Client, MasterClient, Service, Order, BonusLog, Campaign
from src.config import DATABASE_URL

logger = logging.getLogger(__name__)

# Extract database path from URL
DB_PATH = DATABASE_URL.replace("sqlite:///", "") if DATABASE_URL.startswith("sqlite:///") else "db.sqlite3"
MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"

# =============================================================================
# Field Whitelists (SQL Injection Protection)
# =============================================================================

ALLOWED_MASTER_FIELDS = frozenset({
    "name", "sphere", "socials", "contacts", "work_hours", "invite_token",
    "bonus_enabled", "bonus_rate", "bonus_max_spend", "bonus_birthday",
    "gc_connected", "gc_credentials",
    "bonus_welcome", "timezone", "welcome_message", "welcome_photo_id",
    "birthday_message", "birthday_photo_id", "home_message_id", "currency",
    "onboarding_skipped_first_client", "onboarding_banner_shown",
})

ALLOWED_CLIENT_FIELDS = frozenset({
    "tg_id", "name", "phone", "birthday", "registered_via", "consent_given_at",
})

ALLOWED_MASTER_CLIENT_FIELDS = frozenset({
    "bonus_balance", "total_spent", "note", "first_visit", "last_visit",
    "notify_reminders", "notify_marketing", "notify_24h", "notify_1h", "notify_promos",
    "home_message_id", "is_archived",
})

ALLOWED_SERVICE_FIELDS = frozenset({
    "name", "price", "is_active", "description",
})

ALLOWED_ORDER_FIELDS = frozenset({
    "address", "scheduled_at", "status", "payment_type", "amount_total",
    "bonus_accrued", "bonus_spent", "cancel_reason", "gc_event_id", "done_at",
    "reminder_24h_sent", "reminder_1h_sent", "client_confirmed",
})

ALLOWED_NOTIFICATION_FIELDS = frozenset({
    "notify_reminders", "notify_marketing", "notify_24h", "notify_1h", "notify_promos",
})


def _validate_fields(fields: set, allowed: frozenset, table: str) -> None:
    """Validate field names against whitelist. Raises ValueError if invalid."""
    invalid = fields - allowed
    if invalid:
        raise ValueError(f"Invalid fields for {table}: {invalid}")


async def get_connection() -> aiosqlite.Connection:
    """Get a database connection."""
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON")
    return conn


async def init_db() -> None:
    """Initialize database by running all migrations."""
    conn = await get_connection()
    try:
        # Run all migration files in order
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for migration_file in migration_files:
            sql = migration_file.read_text()
            try:
                await conn.executescript(sql)
            except Exception as e:
                logger.debug("Migration %s skipped: %s", migration_file.name, e)
        await conn.commit()
    finally:
        await conn.close()


def _parse_master_row(row) -> Master:
    """Parse a database row into a Master object."""
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
        bonus_welcome=row["bonus_welcome"] if "bonus_welcome" in row.keys() else 0,
        timezone=row["timezone"] if "timezone" in row.keys() else "Europe/Moscow",
        currency=row["currency"] if "currency" in row.keys() else "RUB",
        welcome_message=row["welcome_message"] if "welcome_message" in row.keys() else None,
        welcome_photo_id=row["welcome_photo_id"] if "welcome_photo_id" in row.keys() else None,
        birthday_message=row["birthday_message"] if "birthday_message" in row.keys() else None,
        birthday_photo_id=row["birthday_photo_id"] if "birthday_photo_id" in row.keys() else None,
        gc_connected=bool(row["gc_connected"]),
        gc_credentials=row["gc_credentials"],
        home_message_id=row["home_message_id"] if "home_message_id" in row.keys() else None,
        onboarding_skipped_first_client=bool(row["onboarding_skipped_first_client"]) if "onboarding_skipped_first_client" in row.keys() else False,
        onboarding_banner_shown=bool(row["onboarding_banner_shown"]) if "onboarding_banner_shown" in row.keys() else False,
        created_at=row["created_at"],
    )


def _parse_master_client_row(row) -> MasterClient:
    """Parse a database row into a MasterClient object."""
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
        notify_24h=bool(row["notify_24h"]) if "notify_24h" in row.keys() else True,
        notify_1h=bool(row["notify_1h"]) if "notify_1h" in row.keys() else True,
        notify_promos=bool(row["notify_promos"]) if "notify_promos" in row.keys() else True,
        home_message_id=row["home_message_id"] if "home_message_id" in row.keys() else None,
    )


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
            return _parse_master_row(row)
        return None
    finally:
        await conn.close()


async def get_master_by_id(master_id: int) -> Optional[Master]:
    """Get master by ID."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM masters WHERE id = ?",
            (master_id,)
        )
        row = await cursor.fetchone()
        if row:
            return _parse_master_row(row)
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
            return _parse_master_row(row)
        return None
    finally:
        await conn.close()


async def get_masters() -> list[Master]:
    """Get all masters (used for dev bypass)."""
    conn = await get_connection()
    try:
        cursor = await conn.execute("SELECT * FROM masters LIMIT 1")
        rows = await cursor.fetchall()
        if not rows:
            return []
        columns = [d[0] for d in cursor.description]
        return [_parse_master_row(dict(zip(columns, row))) for row in rows]
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
    timezone: str = "Europe/Moscow",
    currency: str = "RUB",
) -> Master:
    """Create a new master."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO masters (tg_id, name, invite_token, sphere, contacts, socials, work_hours, timezone, currency)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (tg_id, name, invite_token, sphere, contacts, socials, work_hours, timezone, currency)
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
            timezone=timezone,
            currency=currency,
        )
    finally:
        await conn.close()


async def update_master(master_id: int, **kwargs) -> None:
    """Update master fields."""
    if not kwargs:
        return

    # Validate field names against whitelist
    _validate_fields(set(kwargs.keys()), ALLOWED_MASTER_FIELDS, "masters")

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


async def save_master_home_message_id(master_id: int, message_id: int) -> None:
    """Save master's home message ID."""
    await update_master(master_id, home_message_id=message_id)


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


async def get_client_by_id(client_id: int) -> Optional[Client]:
    """Get client by ID."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM clients WHERE id = ?",
            (client_id,)
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

    # Validate field names against whitelist
    _validate_fields(set(kwargs.keys()), ALLOWED_CLIENT_FIELDS, "clients")

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


async def search_clients(master_id: int, query: str) -> list[dict]:
    """Search clients by name or phone (case-insensitive for Cyrillic).

    SQLite's LOWER() doesn't work with Cyrillic, so we fetch more rows
    and filter in Python for proper case-insensitive search.
    """
    conn = await get_connection()
    try:
        # First try phone search in SQL (works fine)
        phone_pattern = f"%{query}%"
        cursor = await conn.execute(
            """
            SELECT c.*, mc.bonus_balance
            FROM clients c
            JOIN master_clients mc ON c.id = mc.client_id
            WHERE mc.master_id = ? AND mc.is_archived = 0 AND c.phone LIKE ?
            ORDER BY c.name
            LIMIT 10
            """,
            (master_id, phone_pattern)
        )
        phone_results = [dict(row) for row in await cursor.fetchall()]

        # Then search by name with Python filtering (for Cyrillic)
        query_lower = query.lower()
        cursor = await conn.execute(
            """
            SELECT c.*, mc.bonus_balance
            FROM clients c
            JOIN master_clients mc ON c.id = mc.client_id
            WHERE mc.master_id = ? AND mc.is_archived = 0
            ORDER BY c.name
            """,
            (master_id,)
        )
        all_rows = await cursor.fetchall()

        # Filter by name in Python (case-insensitive for any language)
        name_results = [
            dict(row) for row in all_rows
            if query_lower in (row["name"] or "").lower()
        ]

        # Merge results, remove duplicates, limit to 10
        seen_ids = set()
        results = []
        for row in phone_results + name_results:
            if row["id"] not in seen_ids:
                seen_ids.add(row["id"])
                results.append(row)
                if len(results) >= 10:
                    break

        return results
    finally:
        await conn.close()


async def get_clients_paginated(master_id: int, page: int = 1, per_page: int = 10) -> tuple[list[dict], int]:
    """Get paginated list of clients.

    Returns: (clients_list, total_count)
    """
    conn = await get_connection()
    try:
        # Get total count
        cursor = await conn.execute(
            "SELECT COUNT(*) as cnt FROM master_clients WHERE master_id = ? AND is_archived = 0",
            (master_id,)
        )
        row = await cursor.fetchone()
        total_count = row["cnt"] if row else 0

        # Get paginated results
        offset = (page - 1) * per_page
        cursor = await conn.execute(
            """
            SELECT c.*, mc.bonus_balance
            FROM clients c
            JOIN master_clients mc ON c.id = mc.client_id
            WHERE mc.master_id = ? AND mc.is_archived = 0
            ORDER BY c.name
            LIMIT ? OFFSET ?
            """,
            (master_id, per_page, offset)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows], total_count
    finally:
        await conn.close()


async def get_archived_clients(master_id: int) -> list[dict]:
    """Get all archived clients for a master."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT c.*, mc.bonus_balance
            FROM clients c
            JOIN master_clients mc ON c.id = mc.client_id
            WHERE mc.master_id = ? AND mc.is_archived = 1
            ORDER BY c.name
            """,
            (master_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_client_with_stats(master_id: int, client_id: int) -> Optional[dict]:
    """Get client with statistics for a master."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT
                c.*,
                mc.bonus_balance,
                mc.total_spent,
                mc.note,
                (SELECT COUNT(*) FROM orders WHERE client_id = c.id AND master_id = ? AND status = 'done') as order_count
            FROM clients c
            JOIN master_clients mc ON c.id = mc.client_id
            WHERE c.id = ? AND mc.master_id = ?
            """,
            (master_id, client_id, master_id)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        await conn.close()


async def get_client_orders(master_id: int, client_id: int, limit: int = 20) -> list[dict]:
    """Get client's order history."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT o.*, GROUP_CONCAT(oi.name, ', ') as services
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.master_id = ? AND o.client_id = ?
            GROUP BY o.id
            ORDER BY o.scheduled_at DESC
            LIMIT ?
            """,
            (master_id, client_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_client_bonus_log(master_id: int, client_id: int, limit: int = 20) -> list[dict]:
    """Get client's bonus log."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT bl.*, o.id as order_id_display
            FROM bonus_log bl
            LEFT JOIN orders o ON bl.order_id = o.id
            WHERE bl.master_id = ? AND bl.client_id = ?
            ORDER BY bl.created_at DESC
            LIMIT ?
            """,
            (master_id, client_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def update_client_note(master_id: int, client_id: int, note: Optional[str]) -> None:
    """Update client note in master_clients."""
    await update_master_client(master_id, client_id, note=note)


async def manual_bonus_transaction(
    master_id: int,
    client_id: int,
    amount: int,
    comment: Optional[str] = None
) -> int:
    """Manual bonus add/subtract. Returns new balance."""
    conn = await get_connection()
    try:
        # Get current balance
        cursor = await conn.execute(
            "SELECT bonus_balance FROM master_clients WHERE master_id = ? AND client_id = ?",
            (master_id, client_id)
        )
        row = await cursor.fetchone()
        current_balance = row["bonus_balance"] if row else 0

        new_balance = current_balance + amount

        # Update balance
        await conn.execute(
            "UPDATE master_clients SET bonus_balance = ? WHERE master_id = ? AND client_id = ?",
            (new_balance, master_id, client_id)
        )

        # Log transaction
        log_type = "manual"
        await conn.execute(
            """
            INSERT INTO bonus_log (master_id, client_id, type, amount, comment)
            VALUES (?, ?, ?, ?, ?)
            """,
            (master_id, client_id, log_type, amount, comment)
        )

        await conn.commit()
        return new_balance
    finally:
        await conn.close()


async def get_client_orders_history(master_id: int, client_id: int, limit: int = 10) -> list[dict]:
    """Get client's order history with status."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT o.*, GROUP_CONCAT(oi.name, ', ') as services
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.master_id = ? AND o.client_id = ?
            GROUP BY o.id
            ORDER BY o.scheduled_at DESC
            LIMIT ?
            """,
            (master_id, client_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


# =============================================================================
# Master-Client relationship
# =============================================================================

async def link_client_to_master(master_id: int, client_id: int) -> MasterClient:
    """Create master-client relationship."""
    conn = await get_connection()
    try:
        await conn.execute(
            """
            INSERT INTO master_clients (master_id, client_id)
            VALUES (?, ?)
            ON CONFLICT(master_id, client_id) DO NOTHING
            """,
            (master_id, client_id)
        )
        await conn.commit()

        cursor = await conn.execute(
            "SELECT * FROM master_clients WHERE master_id = ? AND client_id = ?",
            (master_id, client_id)
        )
        row = await cursor.fetchone()
        return _parse_master_client_row(row)
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
            return _parse_master_client_row(row)
        return None
    finally:
        await conn.close()


async def get_master_client_by_client_tg_id(client_tg_id: int) -> Optional[MasterClient]:
    """Get master-client by client's Telegram ID."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT mc.* FROM master_clients mc
            JOIN clients c ON mc.client_id = c.id
            WHERE c.tg_id = ?
            LIMIT 1
            """,
            (client_tg_id,)
        )
        row = await cursor.fetchone()
        if row:
            return _parse_master_client_row(row)
        return None
    finally:
        await conn.close()


async def get_client_masters(client_id: int) -> list[dict]:
    """Get all masters linked to a client, ordered by last visit."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT m.id as master_id, m.name as master_name, m.sphere,
                   mc.bonus_balance, mc.last_visit,
                   (SELECT COUNT(*) FROM orders
                    WHERE master_id = m.id AND client_id = ? AND status = 'done') as order_count
            FROM masters m
            JOIN master_clients mc ON m.id = mc.master_id
            WHERE mc.client_id = ?
            ORDER BY mc.last_visit DESC NULLS LAST
            """,
            (client_id, client_id),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_all_client_masters_by_tg_id(tg_id: int) -> list[dict]:
    """Get all masters for a client by their Telegram ID. Returns [] if not found."""
    client = await get_client_by_tg_id(tg_id)
    if not client:
        return []
    return await get_client_masters(client.id)


async def link_existing_client_to_master(client_id: int, master_id: int) -> bool:
    """Link existing client to a new master.
    Returns True if linked, False if already linked.
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO master_clients (master_id, client_id)
            VALUES (?, ?)
            ON CONFLICT(master_id, client_id) DO NOTHING
            """,
            (master_id, client_id),
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def update_master_client(master_id: int, client_id: int, **kwargs) -> None:
    """Update master-client relationship fields."""
    if not kwargs:
        return

    # Validate field names against whitelist
    _validate_fields(set(kwargs.keys()), ALLOWED_MASTER_CLIENT_FIELDS, "master_clients")

    conn = await get_connection()
    try:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [master_id, client_id]

        await conn.execute(
            f"UPDATE master_clients SET {set_clause} WHERE master_id = ? AND client_id = ?",
            values
        )
        await conn.commit()
    finally:
        await conn.close()


async def archive_client(master_id: int, client_id: int) -> None:
    """Archive a client (hide from main list)."""
    await update_master_client(master_id, client_id, is_archived=True)


async def restore_client(master_id: int, client_id: int) -> None:
    """Restore archived client."""
    await update_master_client(master_id, client_id, is_archived=False)


async def save_client_home_message_id(master_id: int, client_id: int, message_id: int) -> None:
    """Save client's home message ID."""
    await update_master_client(master_id, client_id, home_message_id=message_id)


async def toggle_client_notification(master_id: int, client_id: int, field: str) -> bool:
    """Toggle a notification setting and return new value."""
    # Validate field name against whitelist
    if field not in ALLOWED_NOTIFICATION_FIELDS:
        raise ValueError(f"Invalid notification field: {field}")

    conn = await get_connection()
    try:
        cursor = await conn.execute(
            f"SELECT {field} FROM master_clients WHERE master_id = ? AND client_id = ?",
            (master_id, client_id)
        )
        row = await cursor.fetchone()
        current_value = bool(row[0]) if row else True
        new_value = not current_value

        await conn.execute(
            f"UPDATE master_clients SET {field} = ? WHERE master_id = ? AND client_id = ?",
            (new_value, master_id, client_id)
        )
        await conn.commit()
        return new_value
    finally:
        await conn.close()


# =============================================================================
# Orders
# =============================================================================

async def get_orders_by_date(master_id: int, target_date: date, all_statuses: bool = False) -> list[dict]:
    """Get orders for a specific date.

    Args:
        master_id: Master ID
        target_date: Date to get orders for
        all_statuses: If True, return all orders including done/cancelled
    """
    conn = await get_connection()
    try:
        if all_statuses:
            cursor = await conn.execute(
                """
                SELECT o.*, c.name as client_name, c.phone as client_phone,
                       GROUP_CONCAT(oi.name, ', ') as services
                FROM orders o
                JOIN clients c ON o.client_id = c.id
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.master_id = ?
                  AND date(o.scheduled_at) = ?
                GROUP BY o.id
                ORDER BY o.scheduled_at
                """,
                (master_id, target_date.isoformat())
            )
        else:
            cursor = await conn.execute(
                """
                SELECT o.*, c.name as client_name, c.phone as client_phone,
                       GROUP_CONCAT(oi.name, ', ') as services
                FROM orders o
                JOIN clients c ON o.client_id = c.id
                LEFT JOIN order_items oi ON o.id = oi.order_id
                WHERE o.master_id = ?
                  AND date(o.scheduled_at) = ?
                  AND o.status IN ('new', 'confirmed')
                GROUP BY o.id
                ORDER BY o.scheduled_at
                """,
                (master_id, target_date.isoformat())
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_orders_today(master_id: int, all_statuses: bool = False) -> list[dict]:
    """Get today's orders for a master."""
    return await get_orders_by_date(master_id, date.today(), all_statuses=all_statuses)


async def get_order_by_id(order_id: int, master_id: int) -> Optional[dict]:
    """Get order by ID with client info and services."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT o.*, c.name as client_name, c.phone as client_phone,
                   c.tg_id as client_tg_id,
                   GROUP_CONCAT(oi.name, ', ') as services
            FROM orders o
            JOIN clients c ON o.client_id = c.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.id = ? AND o.master_id = ?
            GROUP BY o.id
            """,
            (order_id, master_id)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        await conn.close()


async def get_active_dates(master_id: int, year: int, month: int) -> list[date]:
    """Get dates with orders for a given month."""
    conn = await get_connection()
    try:
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        cursor = await conn.execute(
            """
            SELECT DISTINCT date(scheduled_at) as order_date
            FROM orders
            WHERE master_id = ?
              AND date(scheduled_at) >= ?
              AND date(scheduled_at) <= ?
              AND status IN ('new', 'confirmed', 'done')
            """,
            (master_id, first_day.isoformat(), last_day.isoformat())
        )
        rows = await cursor.fetchall()
        return [date.fromisoformat(row["order_date"]) for row in rows]
    finally:
        await conn.close()


# =============================================================================
# Order CRUD
# =============================================================================

async def create_order(
    master_id: int,
    client_id: int,
    address: str,
    scheduled_at: datetime,
    amount_total: int,
    status: str = "new"
) -> int:
    """Create a new order. Returns order_id."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO orders (master_id, client_id, address, scheduled_at, amount_total, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (master_id, client_id, address, scheduled_at.isoformat(), amount_total, status)
        )
        await conn.commit()
        return cursor.lastrowid
    finally:
        await conn.close()


async def create_order_items(order_id: int, services: list[dict]) -> None:
    """Create order items. services = [{"name": str, "price": int}, ...]"""
    conn = await get_connection()
    try:
        for service in services:
            await conn.execute(
                """
                INSERT INTO order_items (order_id, name, price)
                VALUES (?, ?, ?)
                """,
                (order_id, service["name"], service["price"])
            )
        await conn.commit()
    finally:
        await conn.close()


async def get_order_items(order_id: int) -> list[dict]:
    """Get all items (services) for an order."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT id, name, price FROM order_items WHERE order_id = ? ORDER BY id",
            (order_id,)
        )
        rows = await cursor.fetchall()
        return [{"id": row["id"], "name": row["name"], "price": row["price"] or 0} for row in rows]
    finally:
        await conn.close()


async def update_order_status(
    order_id: int,
    status: str,
    required_statuses: Optional[tuple] = None,
    **kwargs,
) -> bool:
    """Update order status and optional fields.

    If required_statuses is given (e.g. ('new', 'confirmed')), the UPDATE adds
    a WHERE status IN (...) guard so the operation is atomic — returns False if
    the row was already in a different status (concurrent request).
    """
    _validate_fields(set(kwargs.keys()) | {"status"}, ALLOWED_ORDER_FIELDS, "orders")

    conn = await get_connection()
    try:
        fields = {"status": status, **kwargs}
        set_clause = ", ".join(f"{k} = ?" for k in fields.keys())
        values = list(fields.values()) + [order_id]

        if required_statuses:
            placeholders = ", ".join("?" for _ in required_statuses)
            sql = f"UPDATE orders SET {set_clause} WHERE id = ? AND status IN ({placeholders})"
            values = values + list(required_statuses)
        else:
            sql = f"UPDATE orders SET {set_clause} WHERE id = ?"

        cursor = await conn.execute(sql, values)
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def update_order_schedule(order_id: int, new_scheduled_at: datetime) -> bool:
    """Update order scheduled time."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE orders SET scheduled_at = ? WHERE id = ?",
            (new_scheduled_at.isoformat(), order_id)
        )
        await conn.commit()
        return True
    finally:
        await conn.close()


async def get_last_client_address(master_id: int, client_id: int) -> Optional[str]:
    """Get last used address for a client."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT address FROM orders
            WHERE master_id = ? AND client_id = ? AND address IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (master_id, client_id)
        )
        row = await cursor.fetchone()
        return row["address"] if row else None
    finally:
        await conn.close()


async def apply_bonus_transaction(
    master_id: int,
    client_id: int,
    order_id: int,
    bonus_spent: int,
    bonus_accrued: int
) -> tuple[int, int]:
    """Apply bonus transaction. Returns (new_balance, total_spent_update)."""
    conn = await get_connection()
    try:
        # Get current balance
        cursor = await conn.execute(
            "SELECT bonus_balance, total_spent FROM master_clients WHERE master_id = ? AND client_id = ?",
            (master_id, client_id)
        )
        row = await cursor.fetchone()
        current_balance = row["bonus_balance"] if row else 0
        current_total_spent = row["total_spent"] if row else 0

        # Calculate new balance
        new_balance = current_balance - bonus_spent + bonus_accrued

        # Get order amount for total_spent
        cursor = await conn.execute(
            "SELECT amount_total FROM orders WHERE id = ?",
            (order_id,)
        )
        order_row = await cursor.fetchone()
        order_amount = order_row["amount_total"] if order_row else 0

        new_total_spent = current_total_spent + order_amount

        # Update master_clients
        await conn.execute(
            """
            UPDATE master_clients
            SET bonus_balance = ?, total_spent = ?, last_visit = CURRENT_TIMESTAMP
            WHERE master_id = ? AND client_id = ?
            """,
            (new_balance, new_total_spent, master_id, client_id)
        )

        # Log bonus spent
        if bonus_spent > 0:
            await conn.execute(
                """
                INSERT INTO bonus_log (master_id, client_id, order_id, type, amount, comment)
                VALUES (?, ?, ?, 'spend', ?, 'Списание за заказ')
                """,
                (master_id, client_id, order_id, -bonus_spent)
            )

        # Log bonus accrued
        if bonus_accrued > 0:
            await conn.execute(
                """
                INSERT INTO bonus_log (master_id, client_id, order_id, type, amount, comment)
                VALUES (?, ?, ?, 'accrual', ?, 'Начисление за заказ')
                """,
                (master_id, client_id, order_id, bonus_accrued)
            )

        await conn.commit()
        return new_balance, order_amount
    finally:
        await conn.close()


async def save_gc_credentials(master_id: int, credentials_json: str) -> None:
    """Save Google Calendar credentials."""
    await update_master(master_id, gc_credentials=credentials_json, gc_connected=True)


async def get_gc_credentials(master_id: int) -> Optional[str]:
    """Get Google Calendar credentials."""
    master = await get_master_by_id(master_id)
    return master.gc_credentials if master else None


async def save_gc_event_id(order_id: int, event_id: str) -> None:
    """Save Google Calendar event ID for an order."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE orders SET gc_event_id = ? WHERE id = ?",
            (event_id, order_id)
        )
        await conn.commit()
    finally:
        await conn.close()


# =============================================================================
# Services
# =============================================================================

async def get_services(master_id: int, active_only: bool = True) -> list[Service]:
    """Get master's services."""
    conn = await get_connection()
    try:
        if active_only:
            cursor = await conn.execute(
                "SELECT * FROM services WHERE master_id = ? AND is_active = 1 ORDER BY name",
                (master_id,)
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM services WHERE master_id = ? ORDER BY name",
                (master_id,)
            )
        rows = await cursor.fetchall()
        return [Service(
            id=row["id"],
            master_id=row["master_id"],
            name=row["name"],
            price=row["price"],
            description=row["description"] if "description" in row.keys() else None,
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        ) for row in rows]
    finally:
        await conn.close()


async def get_archived_services(master_id: int) -> list[Service]:
    """Get master's archived services."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM services WHERE master_id = ? AND is_active = 0 ORDER BY name",
            (master_id,)
        )
        rows = await cursor.fetchall()
        return [Service(
            id=row["id"],
            master_id=row["master_id"],
            name=row["name"],
            price=row["price"],
            description=row["description"] if "description" in row.keys() else None,
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        ) for row in rows]
    finally:
        await conn.close()


async def get_service_by_id(service_id: int) -> Optional[Service]:
    """Get service by ID."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM services WHERE id = ?",
            (service_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Service(
                id=row["id"],
                master_id=row["master_id"],
                name=row["name"],
                price=row["price"],
                description=row["description"] if "description" in row.keys() else None,
                is_active=bool(row["is_active"]),
                created_at=row["created_at"],
            )
        return None
    finally:
        await conn.close()


async def create_service(
    master_id: int,
    name: str,
    price: Optional[int] = None,
    description: Optional[str] = None
) -> Service:
    """Create a new service."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "INSERT INTO services (master_id, name, price, description) VALUES (?, ?, ?, ?)",
            (master_id, name, price, description)
        )
        await conn.commit()
        service_id = cursor.lastrowid

        return Service(
            id=service_id,
            master_id=master_id,
            name=name,
            price=price,
            description=description,
            is_active=True,
        )
    finally:
        await conn.close()


async def update_service(service_id: int, **kwargs) -> None:
    """Update service fields."""
    if not kwargs:
        return

    # Validate field names against whitelist
    _validate_fields(set(kwargs.keys()), ALLOWED_SERVICE_FIELDS, "services")

    conn = await get_connection()
    try:
        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [service_id]

        await conn.execute(
            f"UPDATE services SET {set_clause} WHERE id = ?",
            values
        )
        await conn.commit()
    finally:
        await conn.close()


async def archive_service(service_id: int) -> None:
    """Archive a service (set is_active = 0)."""
    await update_service(service_id, is_active=False)


async def restore_service(service_id: int) -> None:
    """Restore archived service (set is_active = 1)."""
    await update_service(service_id, is_active=True)


# =============================================================================
# Reports
# =============================================================================

async def get_reports(master_id: int, date_from: date, date_to: date) -> dict:
    """Get report data for a period."""
    conn = await get_connection()
    try:
        # Revenue and order count
        cursor = await conn.execute(
            """
            SELECT
                COALESCE(SUM(amount_total), 0) as revenue,
                COUNT(*) as order_count
            FROM orders
            WHERE master_id = ?
              AND status = 'done'
              AND date(done_at) >= ?
              AND date(done_at) <= ?
            """,
            (master_id, date_from.isoformat(), date_to.isoformat())
        )
        row = await cursor.fetchone()
        revenue = row["revenue"] or 0
        order_count = row["order_count"] or 0

        # New clients (added to database in the period)
        cursor = await conn.execute(
            """
            SELECT COUNT(*) as new_clients
            FROM master_clients mc
            JOIN clients c ON mc.client_id = c.id
            WHERE mc.master_id = ?
              AND date(c.created_at) >= ?
              AND date(c.created_at) <= ?
            """,
            (master_id, date_from.isoformat(), date_to.isoformat())
        )
        row = await cursor.fetchone()
        new_clients = row["new_clients"] or 0

        # Repeat clients (clients with 2+ orders total, who had order in period)
        cursor = await conn.execute(
            """
            SELECT COUNT(DISTINCT o.client_id) as repeat_clients
            FROM orders o
            WHERE o.master_id = ?
              AND o.status = 'done'
              AND date(o.done_at) >= ?
              AND date(o.done_at) <= ?
              AND (
                  SELECT COUNT(*) FROM orders o2
                  WHERE o2.client_id = o.client_id
                    AND o2.master_id = o.master_id
                    AND o2.status = 'done'
              ) >= 2
            """,
            (master_id, date_from.isoformat(), date_to.isoformat())
        )
        row = await cursor.fetchone()
        repeat_clients = row["repeat_clients"] or 0

        # Total clients in base
        cursor = await conn.execute(
            "SELECT COUNT(*) as total FROM master_clients WHERE master_id = ?",
            (master_id,)
        )
        row = await cursor.fetchone()
        total_clients = row["total"] or 0

        # Top services by popularity (count only)
        cursor = await conn.execute(
            """
            SELECT oi.name, COUNT(*) as cnt
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.master_id = ?
              AND o.status = 'done'
              AND date(o.done_at) >= ?
              AND date(o.done_at) <= ?
            GROUP BY oi.name
            ORDER BY cnt DESC
            LIMIT 5
            """,
            (master_id, date_from.isoformat(), date_to.isoformat())
        )
        top_services = [
            {"name": row["name"], "count": row["cnt"]}
            for row in await cursor.fetchall()
        ]

        # Top orders by amount (with client name and date)
        cursor = await conn.execute(
            """
            SELECT o.amount_total, c.name as client_name, o.scheduled_at
            FROM orders o
            JOIN clients c ON o.client_id = c.id
            WHERE o.master_id = ?
              AND o.status = 'done'
              AND date(o.done_at) >= ?
              AND date(o.done_at) <= ?
            ORDER BY o.amount_total DESC
            LIMIT 5
            """,
            (master_id, date_from.isoformat(), date_to.isoformat())
        )
        top_orders = [
            {
                "amount": row["amount_total"],
                "client_name": row["client_name"],
                "date": row["scheduled_at"]
            }
            for row in await cursor.fetchall()
        ]

        avg_check = revenue // order_count if order_count > 0 else 0

        return {
            "revenue": revenue,
            "order_count": order_count,
            "new_clients": new_clients,
            "repeat_clients": repeat_clients,
            "avg_check": avg_check,
            "total_clients": total_clients,
            "top_services": top_services,
            "top_orders": top_orders,
        }
    finally:
        await conn.close()


async def get_daily_revenue(
    master_id: int, date_from: date, date_to: date
) -> list[dict]:
    """Get revenue by day for chart. Fills missing days with 0."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT date(done_at) as day, COALESCE(SUM(amount_total), 0) as revenue
            FROM orders
            WHERE master_id = ?
              AND status = 'done'
              AND date(done_at) >= ?
              AND date(done_at) <= ?
            GROUP BY date(done_at)
            """,
            (master_id, date_from.isoformat(), date_to.isoformat())
        )
        rows = await cursor.fetchall()
        revenue_by_day = {row["day"]: row["revenue"] for row in rows}

        result = []
        current = date_from
        while current <= date_to:
            day_str = current.isoformat()
            result.append({"date": day_str, "revenue": revenue_by_day.get(day_str, 0)})
            current += timedelta(days=1)
        return result
    finally:
        await conn.close()


# =============================================================================
# Campaigns
# =============================================================================

async def get_active_campaigns(master_id: int) -> list[Campaign]:
    """Get active promo campaigns for a master."""
    conn = await get_connection()
    try:
        today = date.today().isoformat()
        cursor = await conn.execute(
            """
            SELECT * FROM campaigns
            WHERE master_id = ?
              AND type = 'promo'
              AND (active_from IS NULL OR active_from <= ?)
              AND (active_to IS NULL OR active_to >= ?)
            ORDER BY created_at DESC
            """,
            (master_id, today, today)
        )
        rows = await cursor.fetchall()
        return [Campaign(
            id=row["id"],
            master_id=row["master_id"],
            type=row["type"],
            text=row["text"],
            title=row["title"],
            active_from=row["active_from"],
            active_to=row["active_to"],
            segment=row["segment"],
            sent_at=row["sent_at"],
            sent_count=row["sent_count"],
            created_at=row["created_at"],
        ) for row in rows]
    finally:
        await conn.close()


# =============================================================================
# Reminders and Scheduler
# =============================================================================

async def get_orders_for_reminder_24h() -> list[dict]:
    """Get orders that need 24h reminder.

    Finds orders where:
    - scheduled_at BETWEEN (now + 23h) AND (now + 25h)
    - status IN ('new', 'confirmed')
    - reminder_24h_sent = false
    - client.tg_id IS NOT NULL
    - master_clients.notify_reminders = true
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT
                o.id as order_id,
                o.scheduled_at,
                o.address,
                o.amount_total,
                c.id as client_id,
                c.tg_id as client_tg_id,
                c.name as client_name,
                m.id as master_id,
                m.tg_id as master_tg_id,
                m.name as master_name,
                m.contacts as master_contacts,
                mc.notify_reminders,
                GROUP_CONCAT(oi.name, ', ') as services
            FROM orders o
            JOIN clients c ON o.client_id = c.id
            JOIN masters m ON o.master_id = m.id
            JOIN master_clients mc ON mc.master_id = m.id AND mc.client_id = c.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.status IN ('new', 'confirmed')
              AND o.reminder_24h_sent = 0
              AND c.tg_id IS NOT NULL
              AND mc.notify_reminders = 1
              AND o.scheduled_at BETWEEN datetime('now', '+23 hours') AND datetime('now', '+25 hours')
            GROUP BY o.id
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_orders_for_reminder_1h() -> list[dict]:
    """Get orders that need 1h reminder.

    Finds orders where:
    - scheduled_at BETWEEN (now + 45min) AND (now + 75min)
    - status IN ('new', 'confirmed')
    - reminder_1h_sent = false
    - client.tg_id IS NOT NULL
    - master_clients.notify_reminders = true
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT
                o.id as order_id,
                o.scheduled_at,
                o.address,
                o.amount_total,
                c.id as client_id,
                c.tg_id as client_tg_id,
                c.name as client_name,
                m.id as master_id,
                m.tg_id as master_tg_id,
                m.name as master_name,
                m.contacts as master_contacts,
                mc.notify_reminders,
                GROUP_CONCAT(oi.name, ', ') as services
            FROM orders o
            JOIN clients c ON o.client_id = c.id
            JOIN masters m ON o.master_id = m.id
            JOIN master_clients mc ON mc.master_id = m.id AND mc.client_id = c.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.status IN ('new', 'confirmed')
              AND o.reminder_1h_sent = 0
              AND c.tg_id IS NOT NULL
              AND mc.notify_reminders = 1
              AND o.scheduled_at BETWEEN datetime('now', '+45 minutes') AND datetime('now', '+75 minutes')
            GROUP BY o.id
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_clients_with_birthday_today() -> list[dict]:
    """Get clients with birthday today who should receive bonus.

    Returns clients where:
    - birthday matches today (month-day)
    - master.bonus_enabled = true
    - master.bonus_birthday > 0
    - client.tg_id IS NOT NULL
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT
                c.id as client_id,
                c.tg_id as client_tg_id,
                c.name as client_name,
                m.id as master_id,
                m.tg_id as master_tg_id,
                m.name as master_name,
                m.bonus_birthday,
                m.timezone,
                m.currency,
                m.birthday_message,
                m.birthday_photo_id,
                mc.bonus_balance
            FROM clients c
            JOIN master_clients mc ON mc.client_id = c.id
            JOIN masters m ON mc.master_id = m.id
            WHERE strftime('%m-%d', c.birthday) = strftime('%m-%d', 'now')
              AND m.bonus_enabled = 1
              AND m.bonus_birthday > 0
              AND c.tg_id IS NOT NULL
            """
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def mark_order_confirmed_by_client(order_id: int) -> None:
    """Mark order as confirmed by client."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE orders SET client_confirmed = 1 WHERE id = ?",
            (order_id,)
        )
        await conn.commit()
    finally:
        await conn.close()


async def reset_order_for_reconfirmation(order_id: int) -> None:
    """Reset order flags for new confirmation cycle (used when rescheduling >24h away)."""
    conn = await get_connection()
    try:
        await conn.execute(
            """
            UPDATE orders
            SET reminder_24h_sent = 0,
                reminder_1h_sent = 0,
                client_confirmed = 0
            WHERE id = ?
            """,
            (order_id,)
        )
        await conn.commit()
    finally:
        await conn.close()


async def mark_reminder_sent(order_id: int, reminder_type: str) -> None:
    """Mark reminder as sent.

    Args:
        order_id: Order ID
        reminder_type: '24h' or '1h'
    """
    conn = await get_connection()
    try:
        field = "reminder_24h_sent" if reminder_type == "24h" else "reminder_1h_sent"
        await conn.execute(
            f"UPDATE orders SET {field} = 1 WHERE id = ?",
            (order_id,)
        )
        await conn.commit()
    finally:
        await conn.close()


async def update_master_bonus_setting(master_id: int, field: str, value) -> None:
    """Update a single bonus setting field."""
    allowed_fields = [
        "bonus_welcome", "bonus_birthday", "timezone",
        "welcome_message", "welcome_photo_id",
        "birthday_message", "birthday_photo_id",
    ]
    if field not in allowed_fields:
        raise ValueError(f"Invalid field: {field}")

    conn = await get_connection()
    try:
        await conn.execute(
            f"UPDATE masters SET {field} = ? WHERE id = ?",
            (value, master_id)
        )
        await conn.commit()
    finally:
        await conn.close()


async def accrue_welcome_bonus(master_id: int, client_id: int) -> int:
    """Accrue welcome bonus to client. Returns new balance."""
    conn = await get_connection()
    try:
        # Get master settings
        cursor = await conn.execute(
            "SELECT bonus_welcome, bonus_enabled FROM masters WHERE id = ?",
            (master_id,)
        )
        row = await cursor.fetchone()
        if not row or not row["bonus_enabled"] or row["bonus_welcome"] <= 0:
            # Get current balance
            cursor = await conn.execute(
                "SELECT bonus_balance FROM master_clients WHERE master_id = ? AND client_id = ?",
                (master_id, client_id)
            )
            row = await cursor.fetchone()
            return row["bonus_balance"] if row else 0

        bonus_amount = row["bonus_welcome"]

        # Update balance
        await conn.execute(
            "UPDATE master_clients SET bonus_balance = bonus_balance + ? WHERE master_id = ? AND client_id = ?",
            (bonus_amount, master_id, client_id)
        )

        # Log bonus
        await conn.execute(
            """INSERT INTO bonus_log (master_id, client_id, type, amount, comment)
               VALUES (?, ?, 'welcome', ?, 'Приветственный бонус')""",
            (master_id, client_id, bonus_amount)
        )

        await conn.commit()

        # Get new balance
        cursor = await conn.execute(
            "SELECT bonus_balance FROM master_clients WHERE master_id = ? AND client_id = ?",
            (master_id, client_id)
        )
        row = await cursor.fetchone()
        return row["bonus_balance"] if row else 0
    finally:
        await conn.close()


async def accrue_birthday_bonus(master_id: int, client_id: int) -> int:
    """Accrue birthday bonus to client. Returns new balance.

    Also checks if bonus was already accrued today to prevent duplicates.
    """
    conn = await get_connection()
    try:
        # Check if already accrued today
        cursor = await conn.execute(
            """
            SELECT COUNT(*) as cnt FROM bonus_log
            WHERE master_id = ? AND client_id = ? AND type = 'birthday'
              AND date(created_at) = date('now')
            """,
            (master_id, client_id)
        )
        row = await cursor.fetchone()
        if row["cnt"] > 0:
            # Already accrued today - get current balance
            cursor = await conn.execute(
                "SELECT bonus_balance FROM master_clients WHERE master_id = ? AND client_id = ?",
                (master_id, client_id)
            )
            row = await cursor.fetchone()
            return row["bonus_balance"] if row else 0

        # Get bonus amount from master
        cursor = await conn.execute(
            "SELECT bonus_birthday FROM masters WHERE id = ?",
            (master_id,)
        )
        row = await cursor.fetchone()
        bonus_amount = row["bonus_birthday"] if row else 0

        if bonus_amount <= 0:
            cursor = await conn.execute(
                "SELECT bonus_balance FROM master_clients WHERE master_id = ? AND client_id = ?",
                (master_id, client_id)
            )
            row = await cursor.fetchone()
            return row["bonus_balance"] if row else 0

        # Get current balance
        cursor = await conn.execute(
            "SELECT bonus_balance FROM master_clients WHERE master_id = ? AND client_id = ?",
            (master_id, client_id)
        )
        row = await cursor.fetchone()
        current_balance = row["bonus_balance"] if row else 0
        new_balance = current_balance + bonus_amount

        # Update balance
        await conn.execute(
            "UPDATE master_clients SET bonus_balance = ? WHERE master_id = ? AND client_id = ?",
            (new_balance, master_id, client_id)
        )

        # Log bonus
        await conn.execute(
            """
            INSERT INTO bonus_log (master_id, client_id, type, amount, comment)
            VALUES (?, ?, 'birthday', ?, 'Бонус на день рождения')
            """,
            (master_id, client_id, bonus_amount)
        )

        await conn.commit()
        return new_balance
    finally:
        await conn.close()


async def get_order_for_confirmation(order_id: int, client_tg_id: int) -> Optional[dict]:
    """Get order for confirmation by client.

    Verifies order belongs to client and has valid status.
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT
                o.id as order_id,
                o.scheduled_at,
                o.address,
                o.status,
                c.id as client_id,
                c.name as client_name,
                m.id as master_id,
                m.tg_id as master_tg_id,
                m.name as master_name,
                m.contacts as master_contacts,
                GROUP_CONCAT(oi.name, ', ') as services
            FROM orders o
            JOIN clients c ON o.client_id = c.id
            JOIN masters m ON o.master_id = m.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.id = ? AND c.tg_id = ?
            GROUP BY o.id
            """,
            (order_id, client_tg_id)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await conn.close()


# =============================================================================
# Marketing: Broadcasts and Promos
# =============================================================================

async def get_broadcast_recipients(master_id: int, segment: str) -> list[dict]:
    """Get broadcast recipients by segment.

    Args:
        master_id: Master ID
        segment: 'all' | 'inactive_3m' | 'inactive_6m' | 'new_30d'

    Returns clients with tg_id and notify_marketing = true.
    """
    conn = await get_connection()
    try:
        base_query = """
            SELECT c.id, c.tg_id, c.name
            FROM clients c
            JOIN master_clients mc ON mc.client_id = c.id
            WHERE mc.master_id = ?
              AND c.tg_id IS NOT NULL
              AND mc.notify_marketing = 1
        """

        if segment == "all":
            query = base_query
            params = (master_id,)
        elif segment == "inactive_3m":
            query = base_query + """
              AND (mc.last_visit < datetime('now', '-90 days') OR mc.last_visit IS NULL)
            """
            params = (master_id,)
        elif segment == "inactive_6m":
            query = base_query + """
              AND (mc.last_visit < datetime('now', '-180 days') OR mc.last_visit IS NULL)
            """
            params = (master_id,)
        elif segment == "new_30d":
            query = base_query + """
              AND mc.first_visit > datetime('now', '-30 days')
            """
            params = (master_id,)
        else:
            query = base_query
            params = (master_id,)

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_broadcast_recipients_count(master_id: int, segment: str) -> int:
    """Get count of broadcast recipients by segment."""
    recipients = await get_broadcast_recipients(master_id, segment)
    return len(recipients)


async def get_clients_by_segment(master_id: int, segment: str) -> list[dict]:
    """Get broadcast recipients for Mini App broadcast feature.

    Segments:
      all            — all clients with notify_marketing = 1
      active         — done order in last 30 days
      inactive       — no done order in 60+ days (or no orders at all)
      new            — client registered (created_at) within last 30 days
      birthday_month — birthday in current month
    """
    conn = await get_connection()
    try:
        base_query = """
            SELECT c.id, c.tg_id, c.name
            FROM clients c
            JOIN master_clients mc ON mc.client_id = c.id
            WHERE mc.master_id = ?
              AND c.tg_id IS NOT NULL
              AND mc.notify_marketing = 1
        """

        if segment == "all":
            query = base_query
            params = (master_id,)
        elif segment == "active":
            query = base_query + """
              AND EXISTS (
                SELECT 1 FROM orders o
                WHERE o.master_id = ?
                  AND o.client_id = c.id
                  AND o.status = 'done'
                  AND o.done_at > datetime('now', '-30 days')
              )
            """
            params = (master_id, master_id)
        elif segment == "inactive":
            query = base_query + """
              AND NOT EXISTS (
                SELECT 1 FROM orders o
                WHERE o.master_id = ?
                  AND o.client_id = c.id
                  AND o.status = 'done'
                  AND o.done_at > datetime('now', '-60 days')
              )
            """
            params = (master_id, master_id)
        elif segment == "new":
            query = base_query + """
              AND c.created_at > datetime('now', '-30 days')
            """
            params = (master_id,)
        elif segment == "birthday_month":
            query = base_query + """
              AND c.birthday IS NOT NULL
              AND strftime('%m', c.birthday) = strftime('%m', 'now')
            """
            params = (master_id,)
        else:
            query = base_query
            params = (master_id,)

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def save_campaign(
    master_id: int,
    campaign_type: str,
    title: Optional[str],
    text: Optional[str],
    active_from: Optional[str],
    active_to: Optional[str],
    sent_count: int = 0,
    segment: Optional[str] = None
) -> Campaign:
    """Save a campaign (broadcast or promo)."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO campaigns (master_id, type, title, text, active_from, active_to, sent_count, segment, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (master_id, campaign_type, title, text, active_from, active_to, sent_count, segment)
        )
        await conn.commit()
        campaign_id = cursor.lastrowid

        return Campaign(
            id=campaign_id,
            master_id=master_id,
            type=campaign_type,
            title=title,
            text=text,
            active_from=active_from,
            active_to=active_to,
            segment=segment,
            sent_at=datetime.now().isoformat(),
            sent_count=sent_count,
        )
    finally:
        await conn.close()


async def get_active_promos(master_id: int) -> list[Campaign]:
    """Get active promo campaigns for a master."""
    conn = await get_connection()
    try:
        today = date.today().isoformat()
        cursor = await conn.execute(
            """
            SELECT * FROM campaigns
            WHERE master_id = ?
              AND type = 'promo'
              AND (active_from IS NULL OR active_from <= ?)
              AND (active_to IS NULL OR active_to >= ?)
            ORDER BY created_at DESC
            """,
            (master_id, today, today)
        )
        rows = await cursor.fetchall()
        return [Campaign(
            id=row["id"],
            master_id=row["master_id"],
            type=row["type"],
            title=row["title"],
            text=row["text"],
            active_from=row["active_from"],
            active_to=row["active_to"],
            segment=row["segment"],
            sent_at=row["sent_at"],
            sent_count=row["sent_count"],
            created_at=row["created_at"],
        ) for row in rows]
    finally:
        await conn.close()


async def get_promo_by_id(campaign_id: int, master_id: int) -> Optional[Campaign]:
    """Get promo campaign by ID."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM campaigns WHERE id = ? AND master_id = ? AND type = 'promo'",
            (campaign_id, master_id)
        )
        row = await cursor.fetchone()
        if row:
            return Campaign(
                id=row["id"],
                master_id=row["master_id"],
                type=row["type"],
                title=row["title"],
                text=row["text"],
                active_from=row["active_from"],
                active_to=row["active_to"],
                segment=row["segment"],
                sent_at=row["sent_at"],
                sent_count=row["sent_count"],
                created_at=row["created_at"],
            )
        return None
    finally:
        await conn.close()


async def deactivate_promo(campaign_id: int, master_id: int) -> bool:
    """Deactivate promo by setting active_to to yesterday."""
    conn = await get_connection()
    try:
        yesterday = (date.today() - relativedelta(days=1)).isoformat()
        await conn.execute(
            "UPDATE campaigns SET active_to = ? WHERE id = ? AND master_id = ? AND type = 'promo'",
            (yesterday, campaign_id, master_id)
        )
        await conn.commit()
        return True
    finally:
        await conn.close()


async def get_marketing_recipients_count(master_id: int) -> int:
    """Get count of clients with tg_id and notify_marketing = true."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT COUNT(*) as cnt
            FROM clients c
            JOIN master_clients mc ON mc.client_id = c.id
            WHERE mc.master_id = ?
              AND c.tg_id IS NOT NULL
              AND mc.notify_marketing = 1
            """,
            (master_id,)
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0
    finally:
        await conn.close()


# =============================================================================
# Inbound Requests (client_bot)
# =============================================================================

async def save_inbound_request(
    master_id: int,
    client_id: int,
    type: str,
    text: str = None,
    service_name: str = None,
    file_id: str = None,
    desired_date: str = None,
    desired_time: str = None,
    media_type: str = None,
) -> int:
    """Save inbound request from client.

    Types: 'order_request', 'question', 'media'
    Returns the id of the created request.
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            INSERT INTO inbound_requests
                (master_id, client_id, type, text, service_name, file_id,
                 desired_date, desired_time, media_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (master_id, client_id, type, text, service_name, file_id,
             desired_date, desired_time, media_type)
        )
        await conn.commit()
        return cursor.lastrowid
    finally:
        await conn.close()


async def get_inbound_requests(master_id: int, limit: int = 50) -> list[dict]:
    """Get inbound requests for a master, newest first."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT r.id, r.type, r.text, r.service_name, r.file_id, r.media_type,
                   r.desired_date, r.desired_time, r.is_read,
                   r.created_at,
                   c.name as client_name, c.phone as client_phone,
                   c.tg_id as client_tg_id
            FROM inbound_requests r
            JOIN clients c ON c.id = r.client_id
            WHERE r.master_id = ?
            ORDER BY r.id DESC
            LIMIT ?
            """,
            (master_id, limit)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def mark_request_read(request_id: int, master_id: int) -> bool:
    """Mark a request as read. Returns True if found and updated."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "UPDATE inbound_requests SET is_read = TRUE WHERE id = ? AND master_id = ?",
            (request_id, master_id)
        )
        await conn.commit()
        return cursor.rowcount > 0
    finally:
        await conn.close()


async def mark_all_requests_read(master_id: int) -> None:
    """Mark all requests for a master as read."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE inbound_requests SET is_read = TRUE WHERE master_id = ?",
            (master_id,)
        )
        await conn.commit()
    finally:
        await conn.close()


async def count_pending_requests(master_id: int) -> int:
    """Count pending (new) inbound requests for a master."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT COUNT(*) as cnt FROM inbound_requests WHERE master_id = ? AND is_read = FALSE",
            (master_id,)
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0
    finally:
        await conn.close()


async def count_done_orders(master_id: int) -> int:
    """Count total completed orders for a master."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE master_id = ? AND status = 'done'",
            (master_id,)
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0
    finally:
        await conn.close()


async def get_master_services_for_client(master_id: int) -> list[dict]:
    """Get active services for a master (for client order request)."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT id, name, price
            FROM services
            WHERE master_id = ? AND is_active = 1
            ORDER BY name
            """,
            (master_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


# =============================================================================
# Google Calendar Credentials
# =============================================================================

async def get_gc_credentials(master_id: int) -> Optional[str]:
    """Get Google Calendar credentials JSON for master."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT gc_credentials FROM masters WHERE id = ?",
            (master_id,)
        )
        row = await cursor.fetchone()
        return row["gc_credentials"] if row else None
    finally:
        await conn.close()


async def save_gc_credentials(master_id: int, credentials_json: str) -> None:
    """Save Google Calendar credentials JSON for master."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE masters SET gc_credentials = ?, gc_connected = 1 WHERE id = ?",
            (credentials_json, master_id)
        )
        await conn.commit()
    finally:
        await conn.close()


async def delete_gc_credentials(master_id: int) -> None:
    """Delete Google Calendar credentials for master."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE masters SET gc_credentials = NULL, gc_connected = 0 WHERE id = ?",
            (master_id,)
        )
        await conn.commit()
    finally:
        await conn.close()


async def save_gc_event_id(order_id: int, event_id: str) -> None:
    """Save Google Calendar event ID for order."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE orders SET gc_event_id = ? WHERE id = ?",
            (event_id, order_id)
        )
        await conn.commit()
    finally:
        await conn.close()


async def anonymize_client(client_id: int) -> bool:
    """Anonymize client data (GDPR /delete_me).

    Sets name to 'Удалённый клиент', clears phone, birthday, and tg_id.
    Order history is kept for master's records but becomes anonymized.

    Returns True if successful.
    """
    conn = await get_connection()
    try:
        await conn.execute(
            """
            UPDATE clients
            SET name = 'Удалённый клиент',
                phone = NULL,
                birthday = NULL,
                tg_id = NULL
            WHERE id = ?
            """,
            (client_id,)
        )
        await conn.commit()
        return True
    finally:
        await conn.close()


async def update_client_consent(client_id: int, consent_given_at: str) -> None:
    """Update client consent timestamp."""
    conn = await get_connection()
    try:
        await conn.execute(
            "UPDATE clients SET consent_given_at = ? WHERE id = ?",
            (consent_given_at, client_id)
        )
        await conn.commit()
    finally:
        await conn.close()
