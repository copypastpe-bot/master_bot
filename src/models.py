"""Dataclass models for Master CRM Bot entities."""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


@dataclass
class Master:
    """Master (service provider) model."""
    id: int
    tg_id: int
    name: str
    invite_token: str
    sphere: Optional[str] = None
    socials: Optional[str] = None
    contacts: Optional[str] = None
    work_hours: Optional[str] = None
    bonus_enabled: bool = True
    bonus_rate: float = 5.0
    bonus_max_spend: float = 50.0
    bonus_birthday: int = 300
    gc_connected: bool = False
    gc_credentials: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Client:
    """Client model."""
    id: int
    name: str
    tg_id: Optional[int] = None
    phone: Optional[str] = None
    birthday: Optional[date] = None
    registered_via: Optional[int] = None
    created_at: Optional[datetime] = None


@dataclass
class MasterClient:
    """Master-Client relationship with bonus balance."""
    id: int
    master_id: int
    client_id: int
    bonus_balance: int = 0
    total_spent: int = 0
    note: Optional[str] = None
    first_visit: Optional[datetime] = None
    last_visit: Optional[datetime] = None
    notify_reminders: bool = True
    notify_marketing: bool = True


@dataclass
class Service:
    """Service offered by a master."""
    id: int
    master_id: int
    name: str
    price: Optional[int] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


@dataclass
class Order:
    """Order (appointment) model."""
    id: int
    master_id: int
    client_id: int
    address: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    status: str = "new"
    payment_type: Optional[str] = None
    amount_total: Optional[int] = None
    bonus_accrued: int = 0
    bonus_spent: int = 0
    cancel_reason: Optional[str] = None
    gc_event_id: Optional[str] = None
    created_at: Optional[datetime] = None
    done_at: Optional[datetime] = None


@dataclass
class OrderItem:
    """Order item (service in an order)."""
    id: int
    order_id: int
    name: str
    price: int
    service_id: Optional[int] = None


@dataclass
class BonusLog:
    """Bonus operation log entry."""
    id: int
    master_id: int
    client_id: int
    type: str  # accrual | spend | manual | birthday | promo
    amount: int
    order_id: Optional[int] = None
    comment: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class Campaign:
    """Marketing campaign (promo or broadcast)."""
    id: int
    master_id: int
    type: str  # promo | broadcast
    text: str
    title: Optional[str] = None
    active_from: Optional[date] = None
    active_to: Optional[date] = None
    segment: str = "all"
    sent_at: Optional[datetime] = None
    sent_count: int = 0
    created_at: Optional[datetime] = None


@dataclass
class InboundRequest:
    """Inbound request from client (question, order request, media)."""
    id: int
    master_id: int
    client_id: int
    type: str  # question | order_request | media
    text: Optional[str] = None
    service_name: Optional[str] = None
    file_id: Optional[str] = None
    is_read: bool = False
    created_at: Optional[datetime] = None
