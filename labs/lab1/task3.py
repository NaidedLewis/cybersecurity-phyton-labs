import csv
import datetime
import hashlib
import json
import os
import sys
from functools import wraps

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from shared.student import VARIANT_NUMBER

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
USERS_DB = os.path.join(DATA_DIR, "users.csv")
LOG_FILE = os.path.join(DATA_DIR, "log.json")

PERSONAL_SALT = str(VARIANT_NUMBER).zfill(5)


class ValidationError(Exception):


def log_event(func):

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            status = "success" if result else "failure"
        except Exception:
            status = "error"
            raise
        finally:
            username = args[0] if args else "unknown"
            log_entry = {
                "event": "login",
                "user": username,
                "result": status,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "args": args,
                "kwargs": kwargs,
            }
            try:
                # Читаємо існуючі логи або створюємо новий список
                if os.path.exists(LOG_FILE):
                    with open(LOG_FILE, "r", encoding="utf-8") as f:
                        logs = json.load(f)
                else:
                    logs = []

                logs.append(log_entry)

                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    json.dump(logs, f, indent=4)
            except OSError as e:
                print(f"Помилка запису логів: {e}")

        return result

    return wrapper


def generate_hash(password: str, salt: str = "00000") -> str:
    """Генерує хеш sha3_384 для пароля та солі."""
    if not password or not salt:
        raise ValueError("Пароль або сіль не можуть бути порожніми.")
    if len(password) < 11:
        raise ValidationError("Пароль коротший за мінімальну дозволену довжину (11).")

    combined = password + salt
    # Використовуємо алгоритм sha3_256 для 10 варіанту
    return hashlib.sha3_384(combined.encode("utf-8")).hexdigest()


def create_user(username, password):
    hash_value = generate_hash(password, PERSONAL_SALT)
    return username, hash_value


def create_users(users_list):
    """Створює CSV базу користувачів."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(USERS_DB, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for username, password in users_list:
                try:
                    user_record = create_user(username, password)
                    writer.writerow(user_record)
                except (ValueError, ValidationError) as e:
                    print(f"Пропуск користувача {username}: {e}")
    except PermissionError:
        print("Помилка доступу: немає прав на створення файлу.")
    except OSError as e:
        print(f"Помилка введення/виведення: {e}")


@log_event
def login(username: str, password: str) -> bool:
    """Автентифікація користувача з бази даних."""
    if not username or not password:
        raise ValueError("Логін і пароль є обов'язковими.")

    try:
        with open(USERS_DB, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            users_db = list(reader)

            input_hash = generate_hash(password, PERSONAL_SALT)
            for db_user, db_hash in users_db:
                if db_user == username and db_hash == input_hash:
                    return True
            return False  # <--- Повернули на місце!
    except ValidationError as e:
        print(f"Відмова авторизації (помилка валідації): {e}")
        return False
    except FileNotFoundError:
        print("Базу даних не знайдено.")
        return False


def read_and_display_users():
    """Читання бази даних та вивід у вигляді таблиці (Крок 4)."""
    try:
        with open(USERS_DB, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            users_db = list(reader)

            print("\n--- База користувачів (users_db) ---")
            print(f"{'Логін':<15} | {'Хеш (перші 30 символів)'}")
            print("-" * 50)
            for row in users_db:
                print(f"{row[0]:<15} | {row[1][:30]}...")
    except FileNotFoundError:
        print("Базу даних не знайдено.")


def run_task3():
    print("\n--- Завдання 3. Хешування та Логування ---")

    # Крок 3: 10 записів (як вимагає завдання)
    users_to_register = (
        ("admin", "S0cial@Engineer"),
        ("user1", "Ransomwar3@Protect"),
        ("iot_dev", "Phish1ng@D3tect"),
        ("test", "short"),  # Це викличе ValidationError
        ("hacker", "Zero@D4y123456"),
        ("manager", "Bug@B0unty123"),
        ("guest", "standard1234"),
        ("auditor", "Audit@Pass2026"),
        ("support", "HelpDesk@123"),
        ("ceo", "VeryStrongPass!")
    )

    create_users(users_to_register)

    # Крок 4: Вивід структурованої таблиці
    read_and_display_users()

    print(
        "\nСпроба входу користувача 'admin':",
        "Успіх" if login("admin", "S0cial@Engineer") else "Відмова",
    )
    print(
        "Спроба входу користувача 'user1' (невірний пароль):",
        "Успіх" if login("user1", "WrongPass") else "Відмова",
    )


if __name__ == "__main__":
    run_task3()
