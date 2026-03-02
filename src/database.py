"""Async database layer for Master CRM Bot."""

import aiosqlite
from pathlib import Path
from typing import Optional
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

from src.models import Master, Client, MasterClient, Service, Order, BonusLog, Campaign
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
    """Initialize database by running all migrations."""
    conn = await get_connection()
    try:
        # Run all migration files in order
        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
        for migration_file in migration_files:
            sql = migration_file.read_text()
            try:
                await conn.executescript(sql)
            except Exception:
                pass  # Ignore errors for already applied migrations
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
        gc_connected=bool(row["gc_connected"]),
        gc_credentials=row["gc_credentials"],
        home_message_id=row["home_message_id"] if "home_message_id" in row.keys() else None,
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
    """Search clients by name or phone."""
    conn = await get_connection()
    try:
        search_pattern = f"%{query}%"
        cursor = await conn.execute(
            """
            SELECT c.*, mc.bonus_balance
            FROM clients c
            JOIN master_clients mc ON c.id = mc.client_id
            WHERE mc.master_id = ?
              AND (c.name LIKE ? OR c.phone LIKE ?)
            ORDER BY c.name
            LIMIT 10
            """,
            (master_id, search_pattern, search_pattern)
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
            SELECT * FROM bonus_log
            WHERE master_id = ? AND client_id = ?
            ORDER BY created_at DESC
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


async def update_master_client(master_id: int, client_id: int, **kwargs) -> None:
    """Update master-client relationship fields."""
    if not kwargs:
        return

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


async def save_client_home_message_id(master_id: int, client_id: int, message_id: int) -> None:
    """Save client's home message ID."""
    await update_master_client(master_id, client_id, home_message_id=message_id)


async def toggle_client_notification(master_id: int, client_id: int, field: str) -> bool:
    """Toggle a notification setting and return new value."""
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

async def get_orders_by_date(master_id: int, target_date: date) -> list[dict]:
    """Get orders for a specific date."""
    conn = await get_connection()
    try:
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


async def get_orders_today(master_id: int) -> list[dict]:
    """Get today's orders for a master."""
    return await get_orders_by_date(master_id, date.today())


async def get_order_by_id(order_id: int, master_id: int) -> Optional[dict]:
    """Get order by ID with client info and services."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            """
            SELECT o.*, c.name as client_name, c.phone as client_phone,
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
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        ) for row in rows]
    finally:
        await conn.close()


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

        # New clients
        cursor = await conn.execute(
            """
            SELECT COUNT(DISTINCT client_id) as new_clients
            FROM master_clients
            WHERE master_id = ?
              AND date(first_visit) >= ?
              AND date(first_visit) <= ?
            """,
            (master_id, date_from.isoformat(), date_to.isoformat())
        )
        row = await cursor.fetchone()
        new_clients = row["new_clients"] or 0

        # Repeat clients (had orders before the period)
        cursor = await conn.execute(
            """
            SELECT COUNT(DISTINCT o.client_id) as repeat_clients
            FROM orders o
            WHERE o.master_id = ?
              AND o.status = 'done'
              AND date(o.done_at) >= ?
              AND date(o.done_at) <= ?
              AND EXISTS (
                  SELECT 1 FROM orders o2
                  WHERE o2.client_id = o.client_id
                    AND o2.master_id = o.master_id
                    AND date(o2.done_at) < ?
                    AND o2.status = 'done'
              )
            """,
            (master_id, date_from.isoformat(), date_to.isoformat(), date_from.isoformat())
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

        # Top services
        cursor = await conn.execute(
            """
            SELECT oi.name, SUM(oi.price) as total
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.id
            WHERE o.master_id = ?
              AND o.status = 'done'
              AND date(o.done_at) >= ?
              AND date(o.done_at) <= ?
            GROUP BY oi.name
            ORDER BY total DESC
            LIMIT 5
            """,
            (master_id, date_from.isoformat(), date_to.isoformat())
        )
        top_services = [{"name": row["name"], "total": row["total"]} for row in await cursor.fetchall()]

        avg_check = revenue // order_count if order_count > 0 else 0

        return {
            "revenue": revenue,
            "order_count": order_count,
            "new_clients": new_clients,
            "repeat_clients": repeat_clients,
            "avg_check": avg_check,
            "total_clients": total_clients,
            "top_services": top_services,
        }
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
