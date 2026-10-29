# ЛР №3 — Облік навантаження серверних ресурсів (варіант 10)

Навчальний Web API на FastAPI + SQLite для обліку вимірювань використання
серверних ресурсів.

| Поле | Значення |
|---|---|
| Категорії | `cpu`, `memory`, `disk` (id 1, 2, 3) |
| `value` | використання ресурсу, `float`, 0–100 включно |
| Одиниця | `percent` |
| Поріг | `80.0` — вимірювання з `value >= 80` потребують уваги (`GET /records?min_value=80`) |
| `status` | `new`, `in_progress`, `done` — стан перевірки спостереження |

## Встановлення

Усі команди виконуються з кореня репозиторію в активованому віртуальному середовищі (Python 3.10+):

```bash
pip install -r requirements.txt
```

## База даних і початкові дані

```bash
python -m labs.lab03.database   # створити таблиці (data/lab3.sqlite3)
python -m labs.lab03.seed       # 3 категорії та 8 записів з data/seed.json
```

Повторний запуск `seed` нічого не змінює, якщо база вже містить дані.
Щоб почати з нуля, видаліть `labs/lab03/data/lab3.sqlite3` і запустіть `seed` знову.

## Запуск API

```bash
uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
```

Swagger UI: <http://127.0.0.1:8000/docs>, OpenAPI-схема: <http://127.0.0.1:8000/openapi.json>.

## Маршрути

| Метод | Маршрут | Успіх |
|---|---|---|
| GET | `/ping` | 200 |
| GET | `/student` | 200 |
| GET / POST | `/categories` | 200 / 201 |
| DELETE | `/categories/{category_id}` | 204 (409, якщо є записи) |
| GET | `/records?category_id=&status=&min_value=&q=&limit=20&offset=0` | 200 |
| GET / PUT / DELETE | `/records/{record_id}` | 200 / 200 / 204 |
| POST | `/records` | 201 |
| POST | `/records/bulk` | 201, атомарно: усі записи або жодного |

## Приклади запитів

```bash
curl -i "http://127.0.0.1:8000/ping"
curl -i "http://127.0.0.1:8000/records?category_id=1&status=new&min_value=80&limit=5&offset=0"

curl -i -X POST "http://127.0.0.1:8000/records" \
  -H "Content-Type: application/json" \
  -d '{"code":"V10-TEST","title":"Вимірювання сервера тест","category_id":1,"value":85.5,"status":"new"}'

curl -i -X POST "http://127.0.0.1:8000/records/bulk" \
  -H "Content-Type: application/json" \
  -d '[{"code":"V10-ROLLBACK","title":"Перший елемент","category_id":1,"value":40,"status":"new"},
       {"code":"V10-01","title":"Дублікат коду","category_id":2,"value":50,"status":"new"}]'
# 409 Conflict, V10-ROLLBACK не збережено
```

Усі сценарії перевірки із завдання 3 зібрано в скрипті (сервер має бути запущений, база — щойно заповнена):

```bash
bash labs/lab03/check_api.sh
```

## Структура

```
labs/lab03/
├── main.py           # FastAPI-застосунок, lifespan, /ping, /student
├── database.py       # з'єднання та виконання schema.sql
├── schema.sql        # надана схема (варіанти 10–12)
├── repository.py     # параметризовані SQL-запити, транзакції
├── schemas.py        # Pydantic-моделі
├── config.py         # одиниця, поріг, межі значення
├── seed.py           # початкове заповнення з JSON
├── check_api.sh      # сценарії перевірки
├── routers/          # categories.py, records.py, errors.py
└── data/seed.json    # навчальні дані варіанта
```
