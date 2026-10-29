"""Перетворення помилок шару даних на HTTP-відповіді."""

import logging
import sqlite3

from fastapi import HTTPException, status

from labs.lab03.schemas import ErrorResponse

logger = logging.getLogger("labs.lab03.api")

RESPONSE_404 = {404: {"model": ErrorResponse, "description": "Об'єкт не знайдено"}}
RESPONSE_409 = {
    409: {"model": ErrorResponse, "description": "Конфлікт із наявними даними"}
}

RECORD_NOT_FOUND = "Запис не знайдено"
CATEGORY_NOT_FOUND = "Категорію не знайдено"


def not_found(detail: str) -> HTTPException:
    """Помилка 404 з коротким повідомленням."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def from_integrity_error(error: sqlite3.IntegrityError) -> HTTPException:
    """Зрозуміла HTTP-помилка без SQL-команд і технічних деталей."""
    message = str(error)
    logger.info("Порушення обмеження бази: %s", message)
    if "UNIQUE" in message and "records.code" in message:
        return HTTPException(status.HTTP_409_CONFLICT, "Запис із таким code уже існує")
    if "UNIQUE" in message and "categories.name" in message:
        return HTTPException(
            status.HTTP_409_CONFLICT, "Категорія з такою назвою вже існує"
        )
    if "FOREIGN KEY" in message:
        return HTTPException(
            status.HTTP_409_CONFLICT, "Операція порушує зв'язки між даними"
        )
    return HTTPException(422, "Дані не відповідають обмеженням бази")
