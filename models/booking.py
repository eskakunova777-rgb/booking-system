"""Модель Booking: бронирование стола пользователем на отрезок времени.

Два уровня защиты от двойного бронирования:
1. backend.check_table_availability проверяет пересечения до записи;
2. ограничение EXCLUDE в самой базе не даст записать пересекающиеся
   бронирования одного стола, даже если запись идёт в обход backend.
Отрезок полуоткрытый [начало, конец): бронь 19:00-21:00 и бронь
21:00-23:00 не пересекаются.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Booking:
    __tablename__ = "bookings"
    __columns__ = {
        "id": "SERIAL PRIMARY KEY",
        "user_id": "INT NOT NULL REFERENCES users(id) ON DELETE CASCADE",
        "table_id": "INT NOT NULL REFERENCES tables(id) ON DELETE CASCADE",
        "start_time": "TIMESTAMP NOT NULL",
        "end_time": "TIMESTAMP NOT NULL",
        "guests": "INT NOT NULL DEFAULT 1 CHECK (guests > 0)",
        "created_at": "TIMESTAMP NOT NULL DEFAULT NOW()",
    }
    __constraints__ = [
        "CONSTRAINT bookings_time_order CHECK (end_time > start_time)",
        "CONSTRAINT bookings_no_overlap EXCLUDE USING gist "
        "(table_id WITH =, tsrange(start_time, end_time) WITH &&)",
    ]
    # btree_gist нужно, чтобы в одном EXCLUDE сравнивать и число (table_id), и отрезок времени.
    __extensions__ = ["btree_gist"]

    user_id: int
    table_id: int
    start_time: datetime
    end_time: datetime
    guests: int = 1
    id: Optional[int] = None
    created_at: Optional[datetime] = field(default=None, repr=False)
