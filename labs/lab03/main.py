"""FastAPI-застосунок ЛР №3: облік навантаження серверних ресурсів.

Запуск із кореня репозиторію:
    uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
"""

import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from labs.lab03.config import APP_DESCRIPTION, APP_TITLE, THRESHOLD, UNIT
from labs.lab03.database import initialize_database
from labs.lab03.routers import categories, records
from labs.lab03.schemas import PingResponse, StudentRead
from shared import student

logger = logging.getLogger("labs.lab03.api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Створити відсутні таблиці під час запуску, не змінюючи наявні дані."""
    initialize_database()
    yield


app = FastAPI(
    title=APP_TITLE,
    description=f"{APP_DESCRIPTION}\n\nОдиниця вимірювання: `{UNIT}`, поріг: `{THRESHOLD}`.",
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(categories.router)
app.include_router(records.router)


@app.exception_handler(sqlite3.Error)
def database_error_handler(_: Request, error: sqlite3.Error) -> JSONResponse:
    """Технічні деталі — у журнал, клієнту — зрозуміле повідомлення."""
    logger.exception("Помилка роботи з базою даних: %s", error)
    return JSONResponse(
        status_code=500,
        content={"detail": "Внутрішня помилка роботи з базою даних"},
    )


@app.get("/ping", summary="Перевірка доступності API", tags=["service"])
def ping() -> PingResponse:
    """Повернути `{"status": "ok"}`."""
    return PingResponse(status="ok")


@app.get("/student", summary="Дані студента", tags=["service"])
def get_student() -> StudentRead:
    """ПІБ, група та номер варіанта з `shared/student.py`."""
    return StudentRead(
        student_name=student.STUDENT_NAME,
        group_name=student.GROUP_NAME,
        variant_number=student.VARIANT_NUMBER,
    )
