"""Драйвер PostgreSQL на psycopg2.

Основа взята из прошлого задания (PostgreSQL из Python) и доработана:
- create_tables(models) создаёт таблицы по описанию моделей;
- универсальные insert / select / update / delete для любой таблицы.

Значения всегда передаются параметрами (%s), имена таблиц и колонок
собираются через psycopg2.sql.Identifier, поэтому SQL-инъекции исключены.
Изменения идут внутри `with self.conn:`: при успехе commit, при ошибке rollback.
"""

import os

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


class PostgresDriver:
    def __init__(self):
        load_dotenv()
        self.conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            dbname=os.getenv("DB_NAME", "booking"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
        )

    def close(self):
        if self.conn is not None and not self.conn.closed:
            self.conn.close()

    # ---------- автосоздание таблиц ----------

    @staticmethod
    def build_create_table_sql(model):
        """Собирает CREATE TABLE IF NOT EXISTS по атрибутам модели."""
        parts = [
            sql.SQL("{} {}").format(sql.Identifier(col), sql.SQL(col_type))
            for col, col_type in model.__columns__.items()
        ]
        parts += [sql.SQL(c) for c in getattr(model, "__constraints__", [])]
        return sql.SQL("CREATE TABLE IF NOT EXISTS {} (\n    {}\n)").format(
            sql.Identifier(model.__tablename__),
            sql.SQL(",\n    ").join(parts),
        )

    def create_tables(self, models):
        """Создаёт таблицы для списка моделей (если их ещё нет).

        Возвращает список имён таблиц, которые были созданы впервые.
        """
        created = []
        with self.conn:
            with self.conn.cursor() as cur:
                for model in models:
                    for ext in getattr(model, "__extensions__", []):
                        cur.execute(
                            sql.SQL("CREATE EXTENSION IF NOT EXISTS {}").format(sql.Identifier(ext))
                        )
                    cur.execute("SELECT to_regclass(%s)", (f"public.{model.__tablename__}",))
                    existed = cur.fetchone()[0] is not None
                    cur.execute(self.build_create_table_sql(model))
                    if not existed:
                        created.append(model.__tablename__)
        return created

    # ---------- универсальный CRUD ----------

    def insert(self, table, data):
        """INSERT ... RETURNING *: возвращает созданную строку словарём."""
        cols = list(data.keys())
        query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
            sql.Identifier(table),
            sql.SQL(", ").join(map(sql.Identifier, cols)),
            sql.SQL(", ").join(sql.Placeholder() * len(cols)),
        )
        with self.conn:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, [data[c] for c in cols])
                return dict(cur.fetchone())

    def select(self, table, where=None, order_by="id"):
        """SELECT * с простым фильтром по равенству: where={"phone": "..."}."""
        query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(table))
        params = []
        if where:
            conds = [sql.SQL("{} = %s").format(sql.Identifier(k)) for k in where]
            query += sql.SQL(" WHERE ") + sql.SQL(" AND ").join(conds)
            params = list(where.values())
        if order_by:
            query += sql.SQL(" ORDER BY {}").format(sql.Identifier(order_by))
        return self.fetch_all(query, params)

    def select_by_id(self, table, row_id):
        rows = self.select(table, {"id": row_id})
        return rows[0] if rows else None

    def update(self, table, row_id, data):
        """UPDATE по id; возвращает обновлённую строку или None, если id нет."""
        if not data:
            return self.select_by_id(table, row_id)
        sets = [sql.SQL("{} = %s").format(sql.Identifier(k)) for k in data]
        query = sql.SQL("UPDATE {} SET {} WHERE id = %s RETURNING *").format(
            sql.Identifier(table), sql.SQL(", ").join(sets)
        )
        with self.conn:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, list(data.values()) + [row_id])
                row = cur.fetchone()
                return dict(row) if row else None

    def delete(self, table, row_id):
        """DELETE по id; возвращает True, если строка была удалена."""
        query = sql.SQL("DELETE FROM {} WHERE id = %s").format(sql.Identifier(table))
        with self.conn:
            with self.conn.cursor() as cur:
                cur.execute(query, (row_id,))
                return cur.rowcount > 0

    def fetch_all(self, query, params=None):
        """Произвольный SELECT: список словарей."""
        with self.conn:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query, params or [])
                return [dict(r) for r in cur.fetchall()]
