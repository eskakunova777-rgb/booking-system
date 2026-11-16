"""Backend мини-системы бронирования: CRUD для User, Table, Booking
и проверка доступности стола.

Все функции работают через один общий PostgresDriver (get_driver).
Ошибки базы (дубль телефона, пересечение брони и т.п.) превращаются
в BookingError с понятным текстом, его показывает интерфейс.
"""

from dataclasses import asdict
from datetime import datetime

import psycopg2
from psycopg2 import errorcodes

from models import ALL_MODELS, Booking, Table, User
from postgres_driver import PostgresDriver

USERS = User.__tablename__
TABLES = Table.__tablename__
BOOKINGS = Booking.__tablename__

_driver = None


class BookingError(Exception):
    """Ошибка, которую можно показать пользователю как есть."""


def get_driver():
    global _driver
    if _driver is None or _driver.conn.closed:
        _driver = PostgresDriver()
    return _driver


def close():
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def init_db():
    """Автосоздание таблиц по моделям. Возвращает список созданных таблиц."""
    return get_driver().create_tables(ALL_MODELS)


# ---------- вспомогательное ----------

def parse_dt(value):
    """Принимает datetime или строку 'ГГГГ-ММ-ДД ЧЧ:ММ'."""
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        raise BookingError(f"Дата и время в формате ГГГГ-ММ-ДД ЧЧ:ММ, а пришло: {value!r}")


def _clean(data):
    """Убирает id/created_at и пустые значения из словаря модели."""
    return {k: v for k, v in data.items() if k not in ("id", "created_at") and v is not None}


def _run(action):
    """Выполняет действие с базой и переводит ошибки PostgreSQL на русский."""
    try:
        return action()
    except psycopg2.Error as e:
        code = e.pgcode
        constraint = getattr(e.diag, "constraint_name", None) or ""
        if code == errorcodes.EXCLUSION_VIOLATION:
            raise BookingError("Стол уже занят на это время (сработало ограничение базы).")
        if code == errorcodes.UNIQUE_VIOLATION:
            if "phone" in constraint:
                raise BookingError("Пользователь с таким телефоном уже есть.")
            if "number" in constraint:
                raise BookingError("Стол с таким номером уже есть.")
            raise BookingError("Такая запись уже есть.")
        if code == errorcodes.FOREIGN_KEY_VIOLATION:
            raise BookingError("Нет такого пользователя или стола.")
        if code == errorcodes.CHECK_VIOLATION:
            if "time_order" in constraint:
                raise BookingError("Конец брони должен быть позже начала.")
            raise BookingError("Значение не прошло проверку (места и гости больше нуля).")
        raise BookingError(f"Ошибка базы данных: {e.pgerror or e}")


# ---------- User ----------

def create_user(name, phone, email=None):
    user = User(name=name.strip(), phone=phone.strip(), email=(email or "").strip() or None)
    return _run(lambda: get_driver().insert(USERS, _clean(asdict(user))))


def get_user(user_id):
    return get_driver().select_by_id(USERS, user_id)


def get_user_by_phone(phone):
    rows = get_driver().select(USERS, {"phone": phone})
    return rows[0] if rows else None


def get_all_users():
    return get_driver().select(USERS)


def update_user(user_id, name=None, phone=None, email=None):
    data = _clean({"name": name, "phone": phone, "email": email})
    row = _run(lambda: get_driver().update(USERS, user_id, data))
    if row is None:
        raise BookingError(f"Пользователь id={user_id} не найден.")
    return row


def delete_user(user_id):
    """Удаляет пользователя; его бронирования удаляются вместе с ним (CASCADE)."""
    return get_driver().delete(USERS, user_id)


# ---------- Table ----------

def create_table(number, seats, location=None):
    table = Table(number=int(number), seats=int(seats), location=(location or "").strip() or None)
    return _run(lambda: get_driver().insert(TABLES, _clean(asdict(table))))


def get_table(table_id):
    return get_driver().select_by_id(TABLES, table_id)


def get_table_by_number(number):
    rows = get_driver().select(TABLES, {"number": int(number)})
    return rows[0] if rows else None


def get_all_tables():
    return get_driver().select(TABLES, order_by="number")


def update_table(table_id, number=None, seats=None, location=None):
    data = _clean({
        "number": int(number) if number is not None else None,
        "seats": int(seats) if seats is not None else None,
        "location": location,
    })
    row = _run(lambda: get_driver().update(TABLES, table_id, data))
    if row is None:
        raise BookingError(f"Стол id={table_id} не найден.")
    return row


def delete_table(table_id):
    """Удаляет стол; его бронирования удаляются вместе с ним (CASCADE)."""
    return get_driver().delete(TABLES, table_id)


# ---------- проверка доступности ----------

def check_table_availability(table_id, start_time, end_time, exclude_booking_id=None):
    """Свободен ли стол на отрезке [start_time, end_time).

    Возвращает (True, []) если свободен, иначе (False, список мешающих броней).
    exclude_booking_id нужен при изменении брони: она не мешает сама себе.
    Пересечение: существующая бронь начинается раньше нашего конца
    и заканчивается позже нашего начала.
    """
    start, end = parse_dt(start_time), parse_dt(end_time)
    if end <= start:
        raise BookingError("Конец брони должен быть позже начала.")
    query = """
        SELECT b.id, b.start_time, b.end_time, u.name AS user_name
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        WHERE b.table_id = %s
          AND b.start_time < %s
          AND b.end_time > %s
          AND (%s IS NULL OR b.id <> %s)
        ORDER BY b.start_time
    """
    conflicts = get_driver().fetch_all(query, [table_id, end, start, exclude_booking_id, exclude_booking_id])
    return (len(conflicts) == 0, conflicts)


# ---------- Booking ----------

def _check_booking(user_id, table_id, start, end, guests, exclude_booking_id=None):
    if get_user(user_id) is None:
        raise BookingError(f"Пользователь id={user_id} не найден.")
    table = get_table(table_id)
    if table is None:
        raise BookingError(f"Стол id={table_id} не найден.")
    if guests > table["seats"]:
        raise BookingError(f"За столом №{table['number']} только {table['seats']} мест, а гостей {guests}.")
    free, conflicts = check_table_availability(table_id, start, end, exclude_booking_id)
    if not free:
        c = conflicts[0]
        raise BookingError(
            f"Стол №{table['number']} занят: бронь #{c['id']} ({c['user_name']}) "
            f"{c['start_time']:%d.%m %H:%M}-{c['end_time']:%H:%M}."
        )


def create_booking(user_id, table_id, start_time, end_time, guests=1):
    start, end = parse_dt(start_time), parse_dt(end_time)
    guests = int(guests)
    _check_booking(user_id, table_id, start, end, guests)
    booking = Booking(user_id=user_id, table_id=table_id, start_time=start, end_time=end, guests=guests)
    return _run(lambda: get_driver().insert(BOOKINGS, _clean(asdict(booking))))


def get_booking(booking_id):
    return get_driver().select_by_id(BOOKINGS, booking_id)


def get_all_bookings():
    """Все бронирования с именем гостя и номером стола, по времени начала."""
    return get_driver().fetch_all(
        """
        SELECT b.id, b.user_id, u.name AS user_name, u.phone,
               b.table_id, t.number AS table_number, t.seats,
               b.start_time, b.end_time, b.guests
        FROM bookings b
        JOIN users u  ON u.id = b.user_id
        JOIN tables t ON t.id = b.table_id
        ORDER BY b.start_time, t.number
        """
    )


def update_booking(booking_id, user_id=None, table_id=None, start_time=None, end_time=None, guests=None):
    current = get_booking(booking_id)
    if current is None:
        raise BookingError(f"Бронь id={booking_id} не найдена.")
    new = {
        "user_id": user_id if user_id is not None else current["user_id"],
        "table_id": table_id if table_id is not None else current["table_id"],
        "start_time": parse_dt(start_time) if start_time is not None else current["start_time"],
        "end_time": parse_dt(end_time) if end_time is not None else current["end_time"],
        "guests": int(guests) if guests is not None else current["guests"],
    }
    _check_booking(new["user_id"], new["table_id"], new["start_time"], new["end_time"],
                   new["guests"], exclude_booking_id=booking_id)
    return _run(lambda: get_driver().update(BOOKINGS, booking_id, new))


def delete_booking(booking_id):
    return get_driver().delete(BOOKINGS, booking_id)
