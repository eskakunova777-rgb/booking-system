# Мини-система бронирования столиков

Учебный кейс курса «Вайб-кодер 2.0», урок VPc07, модуль «Базы данных», средний уровень.

Python + PostgreSQL. Три модели (User, Table, Booking), драйвер, который сам создаёт таблицы по моделям,
backend с полным CRUD, проверка доступности стола и окно на tkinter.

## Что внутри

| Файл | Что делает |
|---|---|
| `models/user.py`, `models/table.py`, `models/booking.py` | модели: имя таблицы, колонки с типами, ограничения |
| `postgres_driver.py` | подключение через `.env`, `create_tables(models)` (автосоздание таблиц), универсальные insert / select / update / delete |
| `backend.py` | CRUD для пользователей, столов и бронирований, `check_table_availability` |
| `seed.py` | создаёт таблицы и заносит 3 пользователя, 3 стола и бронирования (повторный запуск дублей не делает) |
| `app.py` | окно на tkinter: вкладки «Бронирования», «Пользователи», «Столы», кнопка «Проверить доступность» |

## Таблицы

- `users`: id, name, phone (уникальный), email, created_at
- `tables`: id, number (уникальный), seats (> 0), location. Имя `tables`, потому что `table` в SQL зарезервировано.
- `bookings`: id, user_id → users, table_id → tables, start_time, end_time, guests, created_at

Удаление пользователя или стола удаляет и его бронирования (`ON DELETE CASCADE`).

## Как не допускаются пересекающиеся брони

Бронь занимает отрезок `[начало, конец)`. Две брони одного стола пересекаются, если одна начинается раньше,
чем закончилась другая. Бронь 19:00-21:00 и бронь 21:00-23:00 не пересекаются.

1. `check_table_availability(table_id, start, end)` ищет пересечения запросом
   `start_time < новый_конец AND end_time > новое_начало` и возвращает `(свободен, мешающие_брони)`.
   `create_booking` и `update_booking` вызывают её перед записью.
2. В самой базе стоит ограничение
   `EXCLUDE USING gist (table_id WITH =, tsrange(start_time, end_time) WITH &&)` (расширение `btree_gist`
   драйвер включает сам). Даже запись в обход backend не создаст двойную бронь.

Ещё проверяется, что гостей не больше, чем мест за столом, и что конец брони позже начала.

## Запуск

Нужны Python 3.10+ и PostgreSQL. Создайте пустую базу `booking` (в pgAdmin или командой):

```bash
createdb -U postgres booking
```

Затем в папке проекта:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Впишите пароль пользователя postgres в `.env` (строка `DB_PASSWORD=`).

```bash
python seed.py
python app.py
```

`seed.py` создаст таблицы и тестовые данные, а в конце покажет, что пересекающаяся бронь не проходит.
`app.py` создаёт таблицы сам, если их нет, так что окно можно запускать и без `seed.py`.

## Функции backend

| Модель | Функции |
|---|---|
| User | `create_user`, `get_user`, `get_user_by_phone`, `get_all_users`, `update_user`, `delete_user` |
| Table | `create_table`, `get_table`, `get_table_by_number`, `get_all_tables`, `update_table`, `delete_table` |
| Booking | `create_booking`, `get_booking`, `get_all_bookings`, `update_booking`, `delete_booking` |
| Проверка | `check_table_availability(table_id, start_time, end_time, exclude_booking_id=None)` |

Время передаётся строкой `ГГГГ-ММ-ДД ЧЧ:ММ` или объектом `datetime`.

Данные в `seed.py` выдуманные, телефоны не настоящие.
