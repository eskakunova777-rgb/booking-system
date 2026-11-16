"""Модель User: гость, который бронирует стол."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class User:
    __tablename__ = "users"
    __columns__ = {
        "id": "SERIAL PRIMARY KEY",
        "name": "TEXT NOT NULL",
        "phone": "TEXT NOT NULL UNIQUE",
        "email": "TEXT",
        "created_at": "TIMESTAMP NOT NULL DEFAULT NOW()",
    }
    __constraints__ = []
    __extensions__ = []

    name: str
    phone: str
    email: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = field(default=None, repr=False)
