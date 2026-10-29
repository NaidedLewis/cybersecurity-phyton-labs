"""Pydantic-моделі запитів і відповідей."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from labs.lab03.config import VALUE_MAX, VALUE_MIN

Status = Literal["new", "in_progress", "done"]

STRICT_INPUT = ConfigDict(str_strip_whitespace=True, extra="forbid")


class CategoryCreate(BaseModel):
    """Дані для створення категорії (ресурсу сервера)."""

    model_config = STRICT_INPUT

    name: str = Field(
        min_length=2,
        max_length=40,
        description="Назва ресурсу, наприклад `cpu`",
        examples=["network"],
    )


class CategoryRead(CategoryCreate):
    """Категорія, збережена в базі."""

    id: int = Field(gt=0, description="Ідентифікатор категорії")


class RecordCreate(BaseModel):
    """Дані для створення вимірювання. `id` задає база."""

    model_config = STRICT_INPUT

    code: str = Field(
        min_length=3,
        max_length=40,
        description="Унікальний код вимірювання",
        examples=["V10-TEST"],
    )
    title: str = Field(
        min_length=3,
        max_length=120,
        description="Назва вимірювання",
        examples=["Вимірювання сервера тест"],
    )
    category_id: int = Field(gt=0, description="Ідентифікатор категорії", examples=[1])
    value: float = Field(
        ge=VALUE_MIN,
        le=VALUE_MAX,
        allow_inf_nan=False,
        description="Використання ресурсу, % (0–100 включно)",
        examples=[85.5],
    )
    status: Status = Field(description="Стан перевірки спостереження", examples=["new"])


class RecordReplace(RecordCreate):
    """Повна заміна змінюваних полів запису: усі поля обов'язкові."""


class RecordRead(RecordCreate):
    """Вимірювання з ідентифікатором і назвою категорії."""

    id: int = Field(gt=0, description="Ідентифікатор запису")
    category_name: str = Field(description="Назва категорії (ресурсу)")


RecordBulk = Annotated[
    list[RecordCreate],
    Field(min_length=1, max_length=100, description="Від 1 до 100 записів"),
]


class SeedCategory(BaseModel):
    """Категорія з початкового JSON з наперед заданим `id`."""

    model_config = STRICT_INPUT

    id: int = Field(gt=0)
    name: str = Field(min_length=2, max_length=40)


class SeedData(BaseModel):
    """Структура файлу `data/seed.json`."""

    model_config = ConfigDict(extra="forbid")

    categories: list[SeedCategory] = Field(min_length=1)
    records: list[RecordCreate] = Field(min_length=1)


class StudentRead(BaseModel):
    """Дані студента з `shared/student.py`."""

    student_name: str
    group_name: str
    variant_number: int


class PingResponse(BaseModel):
    """Відповідь перевірки доступності."""

    status: Literal["ok"]


class ErrorResponse(BaseModel):
    """Тіло відповіді з описом очікуваної помилки."""

    detail: str
