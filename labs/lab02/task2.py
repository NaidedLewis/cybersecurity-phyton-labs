import argparse
import csv
import json
import logging
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Налаштування локального логгера (без LOG015 попереджень)
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_date(date_val) -> datetime:
    """Гнучке перетворення дати у datetime-об'єкт із часовим поясом UTC."""
    if not date_val:
        return datetime.now(timezone.utc)

    if isinstance(date_val, (int, float)):
        return datetime.fromtimestamp(date_val, tz=timezone.utc)

    date_str = str(date_val).strip()

    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)  # noqa: DTZ007
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    logger.warning(
        f"Неможливо розпарсити дату: {date_str}. Використовується поточний час."
    )
    return datetime.now(timezone.utc)


def analyze_ssl_certificates(
    certs_file: str, days_warning: int, output_file: str, fmt: str
):
    path = Path(certs_file)
    if not path.exists():
        logger.error(f"Файл {certs_file} не знайдено.")
        return

    logger.info(f"Loading SSL certificates data from {certs_file}...")
    with open(path, "r", encoding="utf-8") as f:
        certs_data = json.load(f)

    logger.info(f"Audited {len(certs_data)} domain certificates.\n")

    now = datetime.now(timezone.utc)
    issuers = Counter()
    results = []

    expired_count = 0
    warning_count = 0

    print("=== Certificate Expiry & Safety Status ===")
    print(
        f"{'Domain':<22} {'Issuer':<15} {'Days Left':<12} {'Status':<10} {'Signature Alg'}"
    )
    print("-" * 75)

    weak_alg_pattern = re.compile(r"sha1|md5", re.IGNORECASE)

    for cert in certs_data:
        domain = cert.get("Domain") or cert.get("domain") or "Unknown"
        issuer = cert.get("Issuer") or cert.get("issuer") or "Unknown"

        raw_valid_to = (
            cert.get("ValidTo")
            or cert.get("valid_to")
            or cert.get("Valid_To")
            or cert.get("valid_until")
            or cert.get("expiration_date")
        )
        valid_to = parse_date(raw_valid_to)

        sig_alg = (
            cert.get("SignatureAlg")
            or cert.get("signature_alg")
            or cert.get("Signature Algorithm")
            or cert.get("algorithm")
            or "Unknown"
        )

        issuers[issuer] += 1

        days_left = (valid_to - now).days

        if days_left < 0:
            status = "EXPIRED"
            expired_count += 1
        elif days_left <= days_warning:
            status = "WARNING"
            warning_count += 1
        else:
            status = "OK"

        if weak_alg_pattern.search(str(sig_alg)):
            sig_alg_display = f"{sig_alg} (WEAK)"
        else:
            sig_alg_display = str(sig_alg)

        days_left_str = f"{days_left} days"
        print(
            f"{domain:<22} {issuer:<15} {days_left_str:<12} {status:<10} {sig_alg_display}"
        )

        results.append(
            {
                "Domain": domain,
                "Issuer": issuer,
                "DaysLeft": days_left,
                "Status": status,
                "SignatureAlg": sig_alg_display,
            }
        )

    print("\n=== Issuer Statistics ===")
    for iss, count in issuers.items():
        print(f"{iss:<12} : {count}")

    print()
    if expired_count > 0 or warning_count > 0:
        logger.warning(
            f"{expired_count} certificate(s) EXPIRED! {warning_count} certificate(s) expiring within {days_warning} days!"
        )

    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["Domain", "Issuer", "DaysLeft", "Status", "SignatureAlg"]
            )
            writer.writeheader()
            writer.writerows(results)
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4)

    logger.info(f"Report saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Монітор термінів дії SSL/TLS сертифікатів"
    )
    parser.add_argument(
        "--certs-data",
        default="labs/lab02/data/certificates.json",
        help="Шлях до JSON з даними сертифікатів",
    )
    parser.add_argument(
        "--days-warning", type=int, default=30, help="Поріг попередження у днях"
    )
    parser.add_argument(
        "--output-report",
        default="labs/lab02/data/ssl_expiry_report.csv",
        help="Шлях до підсумкового звіту",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="csv",
        help="Формат звіту (json або csv)",
    )

    args = parser.parse_args()
    analyze_ssl_certificates(
        args.certs_data, args.days_warning, args.output_report, args.format
    )


if __name__ == "__main__":
    main()
