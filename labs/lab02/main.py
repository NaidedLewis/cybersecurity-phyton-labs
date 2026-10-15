import sys

from labs.lab02.task1 import Admin, User, UserAccount
from labs.lab02.task2 import main as run_task2


def run_demo():
    print("=== ДЕМОНСТРАЦІЯ ЗАВДАННЯ 1 (ООП) ===")

    # 1. Створення користувача та встановлення пароля
    user = User(username="j_doe", email="j_doe@corp.ua", role="User")
    user.set_password("SecurePassword123!")
    account = UserAccount(user)

    # 2. Успішна та невдала спроба входу
    print("\n--- Перевірка автентифікації ---")
    print(
        "Спроба входу з неправильним паролем:",
        account.login("j_doe", "wrong_pass", "192.168.1.10"),
    )
    print(
        "Спроба входу з правильним паролем:",
        account.login("j_doe", "SecurePassword123!", "192.168.1.10"),
    )
    print("Статус автентифікації:", account.is_authenticated())

    # 3. Валідація email через @property
    print("\n--- Зміна Email ---")
    try:
        user.email = "invalid-email"
    except ValueError as e:
        print("Помилка валідації email (очікувано):", e)

    user.email = "john.doe@corp.ua"
    print("Новий email успішно встановлено:", user.email)

    # 4. Демонстрація класу Admin (наслідування)
    print("\n--- Адміністратор та права ---")
    admin = Admin(
        username="admin_sys", email="admin@corp.ua", permissions=["read", "write"]
    )
    admin.grant_permission("delete")
    print(admin)
    print("Чи є право 'delete'?:", admin.has_permission("delete"))

    # 5. Вихід із системи та перегляд AuditLog
    print("\n--- Завершення сесії та Audit Log ---")
    account.logout()
    print("Статус після logout:", account.is_authenticated())
    account["audit_log"].show_all()


def main():
    if len(sys.argv) < 2:
        print("Використання:")
        print("  python -m labs.lab02.main demo")
        print("  python -m labs.lab02.main analyze [аргументи]")
        return

    command = sys.argv[1]
    if command == "demo":
        run_demo()
    elif command == "analyze":
        # Передаємо решту аргументів у task2
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        run_task2()
    else:
        print(f"Невідома команда: {command}")


if __name__ == "__main__":
    main()
