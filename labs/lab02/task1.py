import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

# Константа таймауту сесії у секундах (15 хвилин)
SESSION_TIMEOUT_SEC = 900


class User:
    """Базовий клас користувача."""

    def __init__(self, username: str, email: str, role: str, active: bool = True):
        self.username = username
        self.role = role
        self.active = active
        self._email = None
        self.email = email  # Викликає сеттер @property для валідації
        self.__password_salt = os.urandom(16)
        self.__password_hash = None

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str):
        # Валідація email за допомогою регулярного виразу
        pattern = r"^[a-zA-Z][a-zA-Z0-9._-]{2,63}@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, value):
            raise ValueError(f"Некоректний формат email: {value}")
        self._email = value

    def set_password(self, password: str):
        """Встановлення пароля з генерацією безпечного хешу (PBKDF2 HMAC SHA-256)."""
        self.__password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), self.__password_salt, 100000
        )

    def check_password(self, password: str) -> bool:
        """Перевірка пароля через безпечне порівняння hmac.compare_digest."""
        if not self.__password_hash:
            return False
        calculated_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), self.__password_salt, 100000
        )
        return hmac.compare_digest(self.__password_hash, calculated_hash)

    def deactivate(self):
        """Деактивація користувача."""
        self.active = False

    def __str__(self) -> str:
        status = "Active" if self.active else "Inactive"
        return f"User({self.username}, Email: {self.email}, Role: {self.role}, Status: {status})"


class Admin(User):
    """Клас адміністратора, що наслідує User."""

    def __init__(
        self,
        username: str,
        email: str,
        permissions: list | set | None = None,
        active: bool = True,
    ):
        super().__init__(username, email, role="Admin", active=active)
        self.permissions = set(permissions) if permissions else set()

    def grant_permission(self, permission: str):
        self.permissions.add(permission)

    def revoke_permission(self, permission: str):
        self.permissions.discard(permission)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def __str__(self) -> str:
        base_str = super().__str__()
        perms = ", ".join(sorted(self.permissions)) if self.permissions else "None"
        return f"{base_str} [Permissions: {perms}]"


class Session:
    """Клас сесії користувача з прив'язкою до часу UTC."""

    def __init__(self, ip: str):
        self.ip = ip
        now = datetime.now(timezone.utc)
        self.login_time = now
        self.last_activity = now

    def touch(self):
        """Оновлення часу останньої активності."""
        self.last_activity = datetime.now(timezone.utc)

    def is_active(self, timeout_sec: int) -> bool:
        """Перевірка, чи активна сесія."""
        if timeout_sec <= 0:
            raise ValueError("Таймаут повинен бути додатним числом")
        now = datetime.now(timezone.utc)
        return (now - self.last_activity) < timedelta(seconds=timeout_sec)


@dataclass
class AuditRecord:
    """Структура запису в журналі аудиту."""

    timestamp: str
    username: str
    action: str


class AuditLog:
    """Журнал аудиту дій користувача."""

    def __init__(self):
        self.records: list[AuditRecord] = []

    def add_log(self, username: str, action: str):
        timestamp = datetime.now(timezone.utc).isoformat()
        self.records.append(
            AuditRecord(timestamp=timestamp, username=username, action=action)
        )

    def show_all(self):
        for rec in self.records:
            print(f"[{rec.timestamp}] User: {rec.username} | Action: {rec.action}")


class UserAccount:
    """Клас-композиція, що об'єднує User, Session та AuditLog."""

    def __init__(self, user: User):
        self.user = user
        self.session = None
        self.audit_log = AuditLog()

    def login(self, username: str, password: str, ip: str) -> bool:
        if not self.user.active or self.user.username != username:
            self.audit_log.add_log(username, "login_failure")
            return False

        if self.user.check_password(password):
            self.session = Session(ip)
            self.session.touch()
            self.audit_log.add_log(username, "login_success")
            return True
        else:
            self.audit_log.add_log(username, "login_failure")
            return False

    def is_authenticated(self) -> bool:
        return bool(self.session and self.session.is_active(SESSION_TIMEOUT_SEC))

    def logout(self):
        if self.user:
            self.audit_log.add_log(self.user.username, "logout")
        self.session = None

    def __getitem__(self, item: str):
        allowed = {
            "user": self.user,
            "session": self.session,
            "audit_log": self.audit_log,
        }
        if item in allowed:
            return allowed[item]
        raise KeyError(f"Доступ до ключа '{item}' заборонено або ключ не існує")

    def __setitem__(self, item: str, value):
        if item == "user":
            if not isinstance(value, User):
                raise TypeError("Значення має бути екземпляром класу User")
            self.user = value
        else:
            raise KeyError(f"Зміна ключа '{item}' не підтримується")
