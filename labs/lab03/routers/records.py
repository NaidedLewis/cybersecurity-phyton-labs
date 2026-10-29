"""Маршрути для записів (вимірювань використання ресурсів)."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Response, status

from labs.lab03 import repository
from labs.lab03.config import VALUE_MAX, VALUE_MIN
from labs.lab03.routers.errors import (
    CATEGORY_NOT_FOUND,
    RECORD_NOT_FOUND,
    RESPONSE_404,
    RESPONSE_409,
    from_integrity_error,
    not_found,
)
from labs.lab03.schemas import (
    RecordBulk,
    RecordCreate,
    RecordRead,
    RecordReplace,
    Status,
)

router = APIRouter(prefix="/records", tags=["records"])

RecordId = Annotated[int, Path(gt=0, description="Ідентифікатор запису (додатне ціле)")]


def _write_error(error: sqlite3.IntegrityError) -> HTTPException:
    """Помилка зміни запису: неіснуюча категорія — 404, інше — за обмеженням."""
    exc = from_integrity_error(error)
    if "FOREIGN KEY" in str(error):
        return not_found(CATEGORY_NOT_FOUND)
    return exc


@router.get("", summary="Список записів із фільтрами", response_model=list[RecordRead])
def list_records(
    category_id: Annotated[
        int | None, Query(gt=0, description="Лише записи цієї категорії")
    ] = None,
    record_status: Annotated[
        Status | None, Query(alias="status", description="Лише записи з цим статусом")
    ] = None,
    min_value: Annotated[
        float | None,
        Query(
            ge=VALUE_MIN,
            le=VALUE_MAX,
            allow_inf_nan=False,
            description="Лише записи з `value >= min_value`, % (0–100)",
        ),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=120,
            description="Буквальний підрядок у `title` (з урахуванням регістру)",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Максимум записів")] = 20,
    offset: Annotated[int, Query(ge=0, description="Скільки записів пропустити")] = 0,
) -> list[dict]:
    """Фільтри поєднуються через `AND`; результати впорядковано за `id`."""
    return repository.list_records(
        category_id=category_id,
        status=record_status,
        min_value=min_value,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/bulk",
    summary="Пакетне створення записів (атомарно)",
    status_code=status.HTTP_201_CREATED,
    response_model=list[RecordRead],
    responses={**RESPONSE_404, **RESPONSE_409},
)
def create_records_bulk(records: RecordBulk) -> list[dict]:
    """Зберегти всі записи пакета в одній транзакції або жодного.

    Дублікат `code` (у базі чи в самому пакеті) — `409`,
    неіснуюча категорія — `404`.
    """
    try:
        return repository.create_records_bulk([item.model_dump() for item in records])
    except repository.CategoryNotFoundError:
        raise not_found(CATEGORY_NOT_FOUND) from None
    except sqlite3.IntegrityError as error:
        raise _write_error(error) from None


@router.get(
    "/{record_id}",
    summary="Отримати запис",
    response_model=RecordRead,
    responses=RESPONSE_404,
)
def get_record(record_id: RecordId) -> dict:
    """Повернути один запис разом із назвою категорії."""
    try:
        return repository.get_record(record_id)
    except repository.RecordNotFoundError:
        raise not_found(RECORD_NOT_FOUND) from None


@router.post(
    "",
    summary="Створити запис",
    status_code=status.HTTP_201_CREATED,
    response_model=RecordRead,
    responses={**RESPONSE_404, **RESPONSE_409},
)
def create_record(record: RecordCreate) -> dict:
    """Створити запис. Неіснуюча категорія — `404`, дублікат `code` — `409`."""
    try:
        return repository.create_record(record.model_dump())
    except repository.CategoryNotFoundError:
        raise not_found(CATEGORY_NOT_FOUND) from None
    except sqlite3.IntegrityError as error:
        raise _write_error(error) from None


@router.put(
    "/{record_id}",
    summary="Повністю замінити змінювані поля запису",
    response_model=RecordRead,
    responses={**RESPONSE_404, **RESPONSE_409},
)
def replace_record(record_id: RecordId, record: RecordReplace) -> dict:
    """Замінити всі п'ять змінюваних полів; `id` залишається незмінним."""
    try:
        return repository.replace_record(record_id, record.model_dump())
    except repository.RecordNotFoundError:
        raise not_found(RECORD_NOT_FOUND) from None
    except repository.CategoryNotFoundError:
        raise not_found(CATEGORY_NOT_FOUND) from None
    except sqlite3.IntegrityError as error:
        raise _write_error(error) from None


@router.delete(
    "/{record_id}",
    summary="Видалити запис",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=RESPONSE_404,
)
def delete_record(record_id: RecordId) -> Response:
    """Видалити запис. Відповідь `204` без тіла."""
    try:
        repository.delete_record(record_id)
    except repository.RecordNotFoundError:
        raise not_found(RECORD_NOT_FOUND) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
