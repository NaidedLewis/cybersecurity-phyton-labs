"""Маршрути для категорій (серверних ресурсів)."""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from labs.lab03 import repository
from labs.lab03.routers.errors import (
    CATEGORY_NOT_FOUND,
    RESPONSE_404,
    RESPONSE_409,
    from_integrity_error,
    not_found,
)
from labs.lab03.schemas import CategoryCreate, CategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])

CategoryId = Annotated[
    int, Path(gt=0, description="Ідентифікатор категорії (додатне ціле)")
]


@router.get("", summary="Список категорій", response_model=list[CategoryRead])
def list_categories() -> list[dict]:
    """Повернути всі категорії за зростанням `id`."""
    return repository.list_categories()


@router.post(
    "",
    summary="Створити категорію",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryRead,
    responses=RESPONSE_409,
)
def create_category(category: CategoryCreate) -> dict:
    """Створити категорію. Дублікат назви — `409`."""
    try:
        return repository.create_category(category.name)
    except sqlite3.IntegrityError as error:
        raise from_integrity_error(error) from None


@router.delete(
    "/{category_id}",
    summary="Видалити порожню категорію",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**RESPONSE_404, **RESPONSE_409},
)
def delete_category(category_id: CategoryId) -> Response:
    """Видалити категорію без записів. Категорія із записами — `409`."""
    try:
        repository.delete_category(category_id)
    except repository.CategoryNotFoundError:
        raise not_found(CATEGORY_NOT_FOUND) from None
    except sqlite3.IntegrityError as error:
        exc = from_integrity_error(error)
        if exc.status_code == status.HTTP_409_CONFLICT:
            exc.detail = "Категорія містить записи, тому її не можна видалити"
        raise exc from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
