# ЛР №2 — Розробка консольних утиліт для задач кібербезпеки

**Варіант 10:** Монітор термінів дії SSL/TLS сертифікатів

## Встановлення

Усі команди виконуються з кореня репозиторію в активованому віртуальному середовищі з ЛР №1 (Python 3.10+):

```bash
pip install -r requirements.txt
```

Для ЛР №2 потрібна лише стандартна бібліотека Python; `ruff` вказано в `requirements.txt`.

## Структура

```text
labs/lab02/
├── __init__.py
├── task1.py      # Завдання 1: User, Admin, Session, AuditRecord, AuditLog, UserAccount
├── task2.py      # Завдання 2: CLI-утиліта аналізу SSL-сертифікатів
├── main.py       # точка входу: команди demo та analyze
├── README.md
└── data/
    └── data_v10/
        └── certificates.json   # вхідні дані з lab2_data.zip (варіант 10)
```

## Вхідні дані

`data/data_v10/certificates.json` — JSON-масив об'єктів з полями
`domain`, `issuer`, `validFrom`, `validTo` (YYYY-MM-DD), `keyLength` (біти), `signatureAlgorithm`.
Назви полів розпізнаються незалежно від регістру та стилю (`validTo`, `ValidTo`, `valid_to`).

## Завдання 1: демонстрація ООП

```bash
python -m labs.lab02.main demo
```

Показує невдалий і успішний вхід, валідацію email через `@property`, права адміністратора,
доступ через `account["user"]` (невідомий ключ — `KeyError`, неправильний тип — `TypeError`),
завершення сеансу за таймаутом (`SESSION_TIMEOUT_SEC = 900`), вихід, вхід деактивованого
користувача та записи `AuditLog`. Імпорт `task1.py` демонстрацію не запускає.

## Завдання 2: аналіз сертифікатів

```bash
python -m labs.lab02.main analyze
python -m labs.lab02.main analyze --certs-data labs/lab02/data/data_v10/certificates.json \
    --days-warning 30 --output-report labs/lab02/data/ssl_expiry_report.csv --format csv
python -m labs.lab02.main analyze --days-warning 60 --format json \
    --output-report labs/lab02/data/ssl_expiry_report.json
```

| Параметр | Типово | Опис |
|---|---|---|
| `--certs-data` | `labs/lab02/data/data_v10/certificates.json` | JSON-файл із сертифікатами |
| `--days-warning` | `30` | поріг попередження, днів (ціле, ≥ 0) |
| `--output-report` | `labs/lab02/data/ssl_expiry_report.csv` | шлях до звіту |
| `--format` | `csv` | формат звіту: `csv` або `json` |

Що робить утиліта:

- рахує дні до закінчення (`validTo` − сьогоднішня дата UTC) і ставить статус
  `EXPIRED` (< 0), `WARNING` (≤ `--days-warning`), `OK` або `INVALID` (немає коректної дати);
- позначає застарілі алгоритми підпису SHA-1 і MD5 (регулярний вираз) та слабкі ключі
  (RSA < 2048 біт, ECDSA < 256 біт);
- рахує сертифікати за видавцями (`collections.Counter`);
- виводить попередження через `logging.warning` і зберігає звіт у CSV або JSON
  (поля `Domain, Issuer, ValidTo, DaysLeft, Status, KeyLength, SignatureAlg, Issues`).

Результат залежить від дати запуску, бо дні рахуються від поточної дати.

## Поведінка при помилках

| Ситуація | Результат |
|---|---|
| файл не існує | `[ERROR] файл не знайдено: ...`, код завершення 1 |
| некоректний JSON або не масив об'єктів | `[ERROR] ...` з поясненням, код 1 |
| запис без коректної дати `validTo` | статус `INVALID`, `[WARNING]` у журналі, аналіз триває |
| від'ємний або нечисловий `--days-warning`, невідомий `--format` | помилка argparse, код 2 |
| звіт не вдається записати | `[ERROR] Не вдалося зберегти звіт ...`, код 1 |
| невідома команда `main` | довідка з використання, код 2 |

## Перевірка стилю

```bash
ruff check .
ruff format --check .
```
