import os
import random
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from shared.student import STUDENT_NAME, VARIANT_NUMBER

passwords = [
    "Social@Engineer",
    "basic",
    "Phishing@D3tect",
    "client",
    "Ransomwar3@Protect",
    "general",
    "Zero@D4y",
    "generic",
    "Bug@Bounty",
    "standard123",
]

criteria = {
    "min_length": 11,
    "require_digits": True,
    "require_upper": True,
    "require_special": True,
}

forbidden_passwords = {"basic", "client", "general", "generic", "standard123", "guest"}


def analyze_passwords():
    print(
        f"--- Завдання 1. Аналіз паролів (Студент: {STUDENT_NAME}, Варіант {VARIANT_NUMBER}) ---"
    )

    random_indices = random.sample(range(len(passwords)), 3)
    for idx in random_indices:
        passwords.append(passwords[idx])

    print(f"{'Пароль':<20} | {'Статус'}")
    print("-" * 40)

    for pwd in passwords:
        length = len(pwd)
        has_digit = any(c.isdigit() for c in pwd)
        has_upper = any(c.isupper() for c in pwd)
        has_lower = any(c.islower() for c in pwd)
        has_special = any(not c.isalnum() for c in pwd)

        criteria_met = sum([has_digit, has_upper, has_lower, has_special])
        is_unique = passwords.count(pwd) == 1

        if pwd in forbidden_passwords or length < criteria["min_length"]:
            status = "Заборонений"
        elif criteria_met == 4 and length >= criteria["min_length"] + 4 and is_unique:
            status = "Дуже сильний"
        elif criteria_met == 4 and length >= criteria["min_length"]:
            status = "Сильний"
        elif criteria_met >= 2 and length >= criteria["min_length"]:
            status = "Середній"
        else:
            status = "Слабкий"

        print(f"{pwd:<20} | {status}")


if __name__ == "__main__":
    analyze_passwords()
