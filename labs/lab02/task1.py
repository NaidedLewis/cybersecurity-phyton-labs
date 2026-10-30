"""Завдання 1: модель користувача, сеансу, журналу аудиту та облікового запису."""

import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import ClassVar

# Час життя сеансу без активності, секунди (15 хвилин)
SESSION_TIMEOUT_SEC = 900
# Кількість ітерацій PBKDF2 для хешування пароля
PBKDF2_ITERATIONS = 100_000
# Довжина випадкової солі, байти
SALT_SIZE = 16

# Локальна частина: починається з латинської літери, 3–64 символи
# з латинських літер, цифр або "_"; далі "@" і доменне ім'я з принаймні однією крапкою.
EMAIL_PATTERN = re.compile(
    r"[A-Za-z][A-Za-z0-9_]{2,63}"
    r"@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+"
)


class User:
    """Базовий клас користувача."""

    def __init__(self, username: str, email: str, role: str, active: bool = True):
        self.username = username
        self.role = role
        self.active = active
        self._email = ""
        self.email = email  # перевірка через сеттер @property
        self.__password_salt = os.urandom(SALT_SIZE)
        self.__password_hash: bytes | None = None

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        if not isinstance(value, str) or not EMAIL_PATTERN.fullmatch(value):
            raise ValueError(f"Некоректний формат email: {value!r}")
        self._email = value

    def _hash(self, password: str) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), self.__password_salt, PBKDF2_ITERATIONS
        )

    def set_password(self, password: str) -> None:
        """Зберегти хеш пароля (PBKDF2-HMAC-SHA256 з нової випадкової солі)."""
        if not password:
            raise ValueError("Пароль не може бути порожнім")
        self.__password_salt = os.urandom(SALT_SIZE)
        self.__password_hash = self._hash(password)

    def check_password(self, password: str) -> bool:
        """Перевірити пароль порівнянням за сталий час (hmac.compare_digest)."""
        if self.__password_hash is None:
            return False
        return hmac.compare_digest(self.__password_hash, self._hash(password))

    def deactivate(self) -> None:
        """Деактивувати користувача."""
        self.active = False

    def __str__(self) -> str:
        status = "Active" if self.active else "Inactive"
        return (
            f"User({self.username}, Email: {self.email}, "
            f"Role: {self.role}, Status: {status})"
        )


class Admin(User):
    """Адміністратор: користувач із набором дозволів (наслідування User)."""

    def __init__(
        self,
        username: str,
        email: str,
        permissions: list[str] | set[str] | None = None,
        active: bool = True,
    ):
        super().__init__(username, email, role="Admin", active=active)
        self.permissions: set[str] = set(permissions) if permissions else set()

    def grant_permission(self, permission: str) -> None:
        self.permissions.add(permission)

    def revoke_permission(self, permission: str) -> None:
        self.permissions.discard(permission)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def __str__(self) -> str:
        perms = ", ".join(sorted(self.permissions)) if self.permissions else "None"
        return f"{super().__str__()} [Permissions: {perms}]"


class Session:
    """Сеанс користувача; час зберігається в UTC."""

    def __init__(self, ip: str):
        self.ip = ip
        now = datetime.now(timezone.utc)
        self.login_time = now
        self.last_activity = now

    def touch(self) -> None:
        """Оновити час останньої активності."""
        self.last_activity = datetime.now(timezone.utc)

    def is_active(self, timeout_sec: int) -> bool:
        """Чи не минуло timeout_sec секунд від останньої активності."""
        if timeout_sec <= 0:
            raise ValueError("Таймаут має бути додатним числом")
        elapsed = datetime.now(timezone.utc) - self.last_activity
        return elapsed < timedelta(seconds=timeout_sec)


@dataclass
class AuditRecord:
    """Один запис журналу аудиту (без паролів)."""

    timestamp: datetime
    username: str
    action: str


class AuditLog:
    """Журнал аудиту дій користувачів."""

    def __init__(self):
        self.records: list[AuditRecord] = []

    def add_log(self, username: str, action: str) -> None:
        self.records.append(
            AuditRecord(datetime.now(timezone.utc), username=username, action=action)
        )

    def show_all(self) -> None:
        for rec in self.records:
            stamp = rec.timestamp.isoformat(timespec="seconds")
            print(f"[{stamp}] User: {rec.username} | Action: {rec.action}")


class UserAccount:
    """Обліковий запис: композиція User, Session та AuditLog."""

    ALLOWED_KEYS: ClassVar[dict[str, type]] = {
        "user": User,
        "session": Session,
        "audit_log": AuditLog,
    }

    def __init__(
        self,
        user: User,
        session: Session | None = None,
        audit_log: AuditLog | None = None,
    ):
        self.user = user
        self.session = session
        self.audit_log = audit_log if audit_log is not None else AuditLog()

    def login(self, username: str, password: str, ip: str) -> bool:
        """Створити сеанс лише після успішної перевірки активності та пароля."""
        if (
            not self.user.active
            or self.user.username != username
            or not self.user.check_password(password)
        ):
            self.audit_log.add_log(username, "login_failure")
            return False
        self.session = Session(ip)
        self.session.touch()
        self.audit_log.add_log(username, "login_success")
        return True

    def is_authenticated(self) -> bool:
        """Чи є сеанс і чи не минув час його дії; перевірка не подовжує сеанс."""
        return self.session is not None and self.session.is_active(SESSION_TIMEOUT_SEC)

    def logout(self) -> None:
        """Завершити сеанс і зафіксувати подію."""
        if self.session is not None:
            self.audit_log.add_log(self.user.username, "logout")
        self.session = None

    def __getitem__(self, key: str):
        if key not in self.ALLOWED_KEYS:
            raise KeyError(key)
        return getattr(self, key)

    def __setitem__(self, key: str, value) -> None:
        if key not in self.ALLOWED_KEYS:
            raise KeyError(key)
        if key == "session" and value is None:
            self.session = None
            return
        expected = self.ALLOWED_KEYS[key]
        if not isinstance(value, expected):
            raise TypeError(f"'{key}' має бути екземпляром {expected.__name__}")
        setattr(self, key, value)


if __name__ == "__main__":
    # Запуск task1.py напряму показує демонстрацію з main.py;
    # при імпорті (import task1) цей блок не виконується
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from labs.lab02.main import run_demo

    run_demo()
