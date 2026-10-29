"""Точка входу ЛР №2: команди demo (Завдання 1) та analyze (Завдання 2).

python -m labs.lab02.main demo
python -m labs.lab02.main analyze [--certs-data ...] [--days-warning N] ...
"""

import sys
from datetime import timedelta

from labs.lab02.task1 import SESSION_TIMEOUT_SEC, Admin, User, UserAccount
from labs.lab02.task2 import main as run_analyze


def run_demo() -> None:
    print("=== ДЕМОНСТРАЦІЯ ЗАВДАННЯ 1 (ООП) ===")

    user = User(username="j_doe", email="j_doe@corp.ua", role="User")
    user.set_password("SecurePassword123!")
    account = UserAccount(user)

    print("\n--- Автентифікація ---")
    print(
        "Вхід з неправильним паролем:",
        account.login("j_doe", "wrong_pass", "192.168.1.10"),
    )
    print(
        "Вхід з правильним паролем:",
        account.login("j_doe", "SecurePassword123!", "192.168.1.10"),
    )
    print("Автентифіковано:", account.is_authenticated())
    print(
        "Пароль у відкритому вигляді не зберігається:",
        "SecurePassword123!" not in vars(user).values(),
    )

    print("\n--- Зміна email із валідацією ---")
    for candidate in ("invalid-email", "1john@corp.ua", "john.doe@corp.ua"):
        try:
            user.email = candidate
        except ValueError as error:
            print("Відхилено:", error)
    user.email = "john_doe@corp.ua"
    print("Новий email:", user.email)

    print("\n--- Адміністратор і права (наслідування) ---")
    admin = Admin(
        username="admin_sys", email="admin@corp.ua", permissions=["read", "write"]
    )
    admin.grant_permission("delete")
    admin.revoke_permission("write")
    print(admin)
    print(
        "Право 'delete':",
        admin.has_permission("delete"),
        "| право 'write':",
        admin.has_permission("write"),
    )

    print("\n--- Доступ через __getitem__ / __setitem__ ---")
    print("account['user'] ->", account["user"])
    for action in (
        lambda: account["password_hash"],
        lambda: account.__setitem__("user", "admin"),
    ):
        try:
            action()
        except (KeyError, TypeError) as error:
            print(f"{type(error).__name__}: {error}")

    print("\n--- Завершення сеансу за таймаутом ---")
    print(f"SESSION_TIMEOUT_SEC = {SESSION_TIMEOUT_SEC}")
    # Імітуємо бездіяльність довшу за таймаут, зсунувши час останньої активності
    account["session"].last_activity -= timedelta(seconds=SESSION_TIMEOUT_SEC + 1)
    print("Автентифіковано після бездіяльності:", account.is_authenticated())
    print("Повторна перевірка не подовжує сеанс:", account.is_authenticated())

    print("\n--- Новий вхід і вихід із системи ---")
    print("Вхід:", account.login("j_doe", "SecurePassword123!", "192.168.1.10"))
    account.logout()
    print("Автентифіковано після logout:", account.is_authenticated())

    print("\n--- Неактивний користувач ---")
    user.deactivate()
    print(
        "Вхід деактивованого користувача:",
        account.login("j_doe", "SecurePassword123!", "192.168.1.10"),
    )

    print("\n--- AuditLog ---")
    account["audit_log"].show_all()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] not in ("demo", "analyze"):
        print("Використання:")
        print("  python -m labs.lab02.main demo")
        print(
            "  python -m labs.lab02.main analyze [--certs-data PATH] [--days-warning N]"
        )
        print(
            "                                    [--output-report PATH] [--format csv|json]"
        )
        return 2
    if args[0] == "demo":
        run_demo()
        return 0
    return run_analyze(args[1:])


if __name__ == "__main__":
    raise SystemExit(main())
