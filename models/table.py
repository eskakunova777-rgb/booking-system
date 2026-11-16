"""Модель Table: столик в ресторане.

Таблица в базе называется tables: слово table в SQL зарезервировано.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Table:
    __tablename__ = "tables"
    __columns__ = {
        "id": "SERIAL PRIMARY KEY",
        "number": "INT NOT NULL UNIQUE",
        "seats": "INT NOT NULL CHECK (seats > 0)",
        "location": "TEXT",
    }
    __constraints__ = []
    __extensions__ = []

    number: int
    seats: int
    location: Optional[str] = None
    id: Optional[int] = None
