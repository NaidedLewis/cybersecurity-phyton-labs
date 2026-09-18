import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

users = {
    "iot_specialist": {
        "role": "iot_security",
        "clearance": 3,
        "department": "IoT",
        "active": True,
    },
    "mobile_analyst": {
        "role": "mobile_security",
        "clearance": 3,
        "department": "Mobile",
        "active": True,
    },
    "web_developer": {
        "role": "web_developer",
        "clearance": 2,
        "department": "Web",
        "active": True,
    },
    "api_consumer": {
        "role": "api_user",
        "clearance": 2,
        "department": "Integration",
        "active": True,
    },
    "demo_account": {
        "role": "demonstration",
        "clearance": 1,
        "department": "Demo",
        "active": False,
    },
}

resources = [
    ("iot_firmware", 3),
    ("mobile_policies", 3),
    ("web_applications", 2),
    ("api_gateway", 2),
    ("device_certificates", 3),
    ("app_store", 1),
    ("vulnerability_database", 3),
    ("device_management", 3),
    ("integration_docs", 2),
    ("demo_content", 1),
]

security_levels = ("Consumer", "Business", "Enterprise", "Critical Systems")
blocked_users = {"demo_account", "compromised_device", "malicious_app"}


def check_access():
    print("\n--- Завдання 2. Контроль доступу ---")
    print("Доступні ресурси:")
    for res_name, res_level in resources:
        level_name = security_levels[res_level - 1]
        print(f"- {res_name} (Рівень: {level_name})")

    print("\nРезультати перевірки доступу:")
    test_users = ["iot_specialist", "web_developer", "demo_account", "hacker99"]

    for username in test_users:
        for res_name, res_level in resources:
            if username not in users:
                result = "DENY (User not found)"
            elif username in blocked_users:
                result = "DENY (User is blocked)"
            elif not users[username].get("active"):
                result = "DENY (Account inactive)"
            elif users[username].get("clearance", 0) >= res_level:
                result = "ALLOW"
            else:
                result = "DENY (Insufficient clearance)"

            print(f"user=[{username}] resource=[{res_name}] -> {result}")


if __name__ == "__main__":
    check_access()
