"""Создаёт таблицы и заносит тестовые данные: 3 пользователя, 3 стола, 2 брони.

Повторный запуск дублей не создаёт: каждая запись сначала ищется.
В конце показывает, что пересекающуюся бронь система не пропускает.
Данные выдуманные, телефоны не настоящие.
"""

import backend
from backend import BookingError

USERS = [
    ("Анна Смирнова", "+7 900 000-00-01", "anna@example.com"),
    ("Борис Кузнецов", "+7 900 000-00-02", None),
    ("Вера Орлова", "+7 900 000-00-03", "vera@example.com"),
]
TABLES = [
    (1, 2, "у окна"),
    (2, 4, "центр зала"),
    (3, 6, "веранда"),
]
# (телефон гостя, номер стола, начало, конец, гостей)
BOOKINGS = [
    ("+7 900 000-00-01", 1, "2026-11-20 19:00", "2026-11-20 21:00", 2),
    ("+7 900 000-00-02", 2, "2026-11-20 20:00", "2026-11-20 22:00", 4),
    ("+7 900 000-00-03", 3, "2026-11-21 13:00", "2026-11-21 15:00", 5),
]


def main():
    created = backend.init_db()
    print("Таблицы созданы:", ", ".join(created) if created else "уже были")

    users = {}
    for name, phone, email in USERS:
        row = backend.get_user_by_phone(phone) or backend.create_user(name, phone, email)
        users[phone] = row["id"]

    tables = {}
    for number, seats, location in TABLES:
        row = backend.get_table_by_number(number) or backend.create_table(number, seats, location)
        tables[number] = row["id"]

    existing = {(b["table_id"], b["start_time"].strftime("%Y-%m-%d %H:%M")) for b in backend.get_all_bookings()}
    for phone, number, start, end, guests in BOOKINGS:
        if (tables[number], start) in existing:
            continue
        backend.create_booking(users[phone], tables[number], start, end, guests)

    print(f"Пользователей: {len(backend.get_all_users())}, столов: {len(backend.get_all_tables())}")
    print("\nБронирования:")
    for b in backend.get_all_bookings():
        print(f"  #{b['id']}: стол №{b['table_number']}, {b['user_name']}, "
              f"{b['start_time']:%d.%m.%Y %H:%M}-{b['end_time']:%H:%M}, гостей {b['guests']}")

    print("\nПроверка: Вера хочет стол №1 на 20.11 20:00-22:00 (пересекается с бронью Анны)")
    free, conflicts = backend.check_table_availability(tables[1], "2026-11-20 20:00", "2026-11-20 22:00")
    print("  check_table_availability:", "свободен" if free else f"занят, мешает бронь #{conflicts[0]['id']}")
    try:
        backend.create_booking(users["+7 900 000-00-03"], tables[1], "2026-11-20 20:00", "2026-11-20 22:00", 2)
        print("  create_booking: создана (так быть не должно)")
    except BookingError as e:
        print("  create_booking отказал:", e)

    print("\nПроверка: стол №1 на 20.11 21:00-23:00 (сразу после Анны)")
    free, _ = backend.check_table_availability(tables[1], "2026-11-20 21:00", "2026-11-20 23:00")
    print("  check_table_availability:", "свободен" if free else "занят")

    backend.close()


if __name__ == "__main__":
    main()
