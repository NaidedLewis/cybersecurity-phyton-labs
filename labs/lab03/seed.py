"""Початкове заповнення бази навчальними даними з `data/seed.json`.

Запуск із кореня репозиторію: `python -m labs.lab03.seed`
"""

import json
import logging
import sqlite3
import sys
from pathlib import Path

from pydantic import ValidationError

from labs.lab03.database import BASE_DIR, initialize_database
from labs.lab03.repository import INSERT_RECORD, write_transaction
from labs.lab03.schemas import SeedData

SEED_PATH = BASE_DIR / "data" / "seed.json"

logger = logging.getLogger(__name__)


def load_seed(path: Path = SEED_PATH) -> SeedData:
    """Прочитати JSON і перевірити його через Pydantic."""
    with path.open(encoding="utf-8") as file:
        raw = json.load(file)
    return SeedData.model_validate(raw)


def seed_database(data: SeedData) -> bool:
    """Заповнити порожню базу в одній транзакції.

    Повертає `False`, якщо база вже містить дані: тоді нічого не змінюється.
    """
    with write_transaction() as connection:
        categories = connection.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        records = connection.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        if categories or records:
            return False
        connection.executemany(
            "INSERT INTO categories (id, name) VALUES (?, ?)",
            [(category.id, category.name) for category in data.categories],
        )
        connection.executemany(
            INSERT_RECORD,
            [record.model_dump() for record in data.records],
        )
    return True


def main() -> int:
    """Точка входу: ініціалізація бази та початкове заповнення."""
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    try:
        initialize_database()
        data = load_seed()
    except (OSError, json.JSONDecodeError) as error:
        logger.error("Не вдалося прочитати початкові дані: %s", error)
        return 1
    except ValidationError as error:
        logger.error("Початкові дані некоректні:\n%s", error)
        return 1

    try:
        inserted = seed_database(data)
    except sqlite3.IntegrityError as error:
        logger.error(
            "Дані порушують обмеження бази, жодних змін не збережено: %s", error
        )
        return 1

    if inserted:
        print(
            f"Базу заповнено: категорій — {len(data.categories)}, "
            f"записів — {len(data.records)}."
        )
    else:
        print("База вже містить дані; повторне заповнення пропущено, дані не змінено.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
