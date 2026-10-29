"""Шар доступу до даних: параметризовані SQL-запити до SQLite.

Модуль не залежить від FastAPI. Відсутні записи та категорії
повідомляються власними винятками, а порушення обмежень бази
(`sqlite3.IntegrityError`) передаються шару API без змін.
"""

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import closing, contextmanager
from typing import Any

from labs.lab03.database import get_connection

Row = dict[str, Any]

RECORD_FIELDS = ("code", "title", "category_id", "value", "status")

SELECT_RECORDS = """
    SELECT r.id, r.code, r.title, r.category_id, r.value, r.status,
           c.name AS category_name
    FROM records AS r
    JOIN categories AS c ON c.id = r.category_id
"""

INSERT_RECORD = """
    INSERT INTO records (code, title, category_id, value, status)
    VALUES (:code, :title, :category_id, :value, :status)
"""


class NotFoundError(Exception):
    """Базовий виняток: потрібний об'єкт відсутній у базі."""


class RecordNotFoundError(NotFoundError):
    """Запис з указаним `id` не існує."""


class CategoryNotFoundError(NotFoundError):
    """Категорія з указаним `id` не існує."""


@contextmanager
def open_connection() -> Iterator[sqlite3.Connection]:
    """Відкрити з'єднання для однієї операції та гарантовано закрити його."""
    with closing(get_connection()) as connection:
        connection.row_factory = sqlite3.Row
        yield connection


@contextmanager
def write_transaction() -> Iterator[sqlite3.Connection]:
    """Транзакція зміни даних: commit за успіху, rollback за винятку.

    `BEGIN IMMEDIATE` одразу бере блокування запису, тому перевірки
    існування та подальші зміни виконуються в одній транзакції.
    """
    with open_connection() as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        yield connection


def _record_values(data: dict[str, Any]) -> dict[str, Any]:
    """Залишити лише змінювані поля запису."""
    return {field: data[field] for field in RECORD_FIELDS}


def _category_exists(connection: sqlite3.Connection, category_id: int) -> bool:
    row = connection.execute(
        "SELECT 1 FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    return row is not None


def _require_category(connection: sqlite3.Connection, category_id: int) -> None:
    if not _category_exists(connection, category_id):
        raise CategoryNotFoundError(category_id)


def _fetch_record(connection: sqlite3.Connection, record_id: int) -> Row | None:
    row = connection.execute(
        SELECT_RECORDS + " WHERE r.id = ?", (record_id,)
    ).fetchone()
    return dict(row) if row is not None else None


# ---------------------------------------------------------------- categories


def list_categories() -> list[Row]:
    """Повернути всі категорії за зростанням `id`."""
    with open_connection() as connection:
        rows = connection.execute(
            "SELECT id, name FROM categories ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def create_category(name: str) -> Row:
    """Створити категорію; дублікат назви спричиняє `IntegrityError`."""
    with write_transaction() as connection:
        cursor = connection.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        category_id = cursor.lastrowid
    return {"id": category_id, "name": name}


def delete_category(category_id: int) -> None:
    """Видалити категорію.

    Якщо категорія містить записи, `ON DELETE RESTRICT` спричиняє
    `IntegrityError`, і транзакція скасовується.
    """
    with write_transaction() as connection:
        _require_category(connection, category_id)
        connection.execute("DELETE FROM categories WHERE id = ?", (category_id,))


# ------------------------------------------------------------------- records


def get_record(record_id: int) -> Row:
    """Повернути запис разом із назвою категорії."""
    with open_connection() as connection:
        record = _fetch_record(connection, record_id)
    if record is None:
        raise RecordNotFoundError(record_id)
    return record


def list_records(
    *,
    category_id: int | None = None,
    status: str | None = None,
    min_value: float | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Row]:
    """Повернути сторінку записів, що задовольняють усі задані фільтри.

    SQL-фрагменти умов беруться лише з рядків цієї функції, а всі
    значення передаються окремим списком параметрів.
    """
    conditions: list[str] = []
    params: list[Any] = []
    if category_id is not None:
        conditions.append("r.category_id = ?")
        params.append(category_id)
    if status is not None:
        conditions.append("r.status = ?")
        params.append(status)
    if min_value is not None:
        conditions.append("r.value >= ?")
        params.append(min_value)
    if q is not None:
        conditions.append("instr(r.title, ?) > 0")
        params.append(q)

    sql = SELECT_RECORDS
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY r.id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with open_connection() as connection:
        rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def create_record(data: dict[str, Any]) -> Row:
    """Додати запис; неіснуюча категорія — `CategoryNotFoundError`."""
    values = _record_values(data)
    with write_transaction() as connection:
        _require_category(connection, values["category_id"])
        cursor = connection.execute(INSERT_RECORD, values)
        record = _fetch_record(connection, cursor.lastrowid)
    return record


def replace_record(record_id: int, data: dict[str, Any]) -> Row:
    """Повністю замінити змінювані поля запису; `id` не змінюється."""
    values = _record_values(data)
    with write_transaction() as connection:
        if _fetch_record(connection, record_id) is None:
            raise RecordNotFoundError(record_id)
        _require_category(connection, values["category_id"])
        connection.execute(
            """
            UPDATE records
            SET code = :code, title = :title, category_id = :category_id,
                value = :value, status = :status
            WHERE id = :id
            """,
            {**values, "id": record_id},
        )
        record = _fetch_record(connection, record_id)
    return record


def delete_record(record_id: int) -> None:
    """Видалити запис; відсутній `id` — `RecordNotFoundError`."""
    with write_transaction() as connection:
        if _fetch_record(connection, record_id) is None:
            raise RecordNotFoundError(record_id)
        connection.execute("DELETE FROM records WHERE id = ?", (record_id,))


def create_records_bulk(items: Sequence[dict[str, Any]]) -> list[Row]:
    """Додати пакет записів атомарно, в одній транзакції.

    Спочатку перевіряються всі категорії, далі всі записи вставляються
    одним `executemany`. Будь-яка помилка скасовує весь пакет.
    """
    values = [_record_values(item) for item in items]
    category_ids = sorted({item["category_id"] for item in values})
    placeholders = ", ".join("?" for _ in category_ids)

    with write_transaction() as connection:
        found = {
            row["id"]
            for row in connection.execute(
                f"SELECT id FROM categories WHERE id IN ({placeholders})",
                category_ids,
            )
        }
        missing = [cid for cid in category_ids if cid not in found]
        if missing:
            raise CategoryNotFoundError(missing[0])

        before = connection.execute(
            "SELECT COALESCE(MAX(id), 0) FROM records"
        ).fetchone()[0]
        connection.executemany(INSERT_RECORD, values)
        codes = [item["code"] for item in values]
        code_placeholders = ", ".join("?" for _ in codes)
        rows = connection.execute(
            SELECT_RECORDS
            + f" WHERE r.id > ? AND r.code IN ({code_placeholders}) ORDER BY r.id",
            [before, *codes],
        ).fetchall()
    return [dict(row) for row in rows]


def count_records() -> int:
    """Кількість записів (для перевірки скасування пакета)."""
    with open_connection() as connection:
        return connection.execute("SELECT COUNT(*) FROM records").fetchone()[0]
