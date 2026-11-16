"""Модели мини-системы бронирования.

Каждая модель описывает одну таблицу: имя таблицы, колонки с типами
и дополнительные ограничения. По этому описанию драйвер сам создаёт
таблицы в базе (PostgresDriver.create_tables).
"""

from models.user import User
from models.table import Table
from models.booking import Booking

# Порядок важен: Booking ссылается на users и tables, поэтому создаётся последней.
ALL_MODELS = [User, Table, Booking]

__all__ = ["User", "Table", "Booking", "ALL_MODELS"]
