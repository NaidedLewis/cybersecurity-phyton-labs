"""Завдання 2 (варіант 10): монітор термінів дії SSL/TLS сертифікатів."""

import argparse
import csv
import json
import logging
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

logger = logging.getLogger("ssl_monitor")

DEFAULT_CERTS = Path("labs/lab02/data/data_v10/certificates.json")
DEFAULT_REPORT = Path("labs/lab02/data/ssl_expiry_report.csv")

# Застарілі алгоритми підпису: SHA-1 та MD5
WEAK_SIGNATURE = re.compile(r"sha-?1(?!\d)|md5", re.IGNORECASE)
ECDSA_SIGNATURE = re.compile(r"ecdsa", re.IGNORECASE)
# Мінімальна довжина ключа, біти
MIN_RSA_KEY = 2048
MIN_ECDSA_KEY = 256

FIELDS = [
    "Domain",
    "Issuer",
    "ValidTo",
    "DaysLeft",
    "Status",
    "KeyLength",
    "SignatureAlg",
    "Issues",
]


@dataclass
class CertResult:
    """Результат перевірки одного сертифіката."""

    Domain: str
    Issuer: str
    ValidTo: str
    DaysLeft: int | None
    Status: str
    KeyLength: int | None
    SignatureAlg: str
    Issues: str


def normalize_keys(record: dict) -> dict:
    """validTo, Valid_To, valid to -> validto: стійкість до стилю назв полів."""
    return {re.sub(r"[^a-z0-9]", "", str(k).lower()): v for k, v in record.items()}


def pick(record: dict, *names: str):
    for name in names:
        value = record.get(name)
        if value not in (None, ""):
            return value
    return None


def parse_date(value) -> date | None:
    """Дата закінчення як date; None, якщо значення відсутнє або некоректне."""
    if value is None:
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc).date()
        except ValueError:
            continue
    return None


def evaluate(cert: dict, today: date, days_warning: int) -> CertResult:
    """Розрахувати дні до закінчення, статус і слабкі місця сертифіката."""
    rec = normalize_keys(cert)
    domain = str(pick(rec, "domain", "host", "cn") or "Unknown")
    issuer = str(pick(rec, "issuer") or "Unknown")
    sig_alg = str(
        pick(rec, "signaturealgorithm", "signaturealg", "algorithm") or "Unknown"
    )
    raw_valid_to = pick(rec, "validto", "notafter", "validuntil", "expirationdate")
    valid_to = parse_date(raw_valid_to)

    raw_key = pick(rec, "keylength", "keysize", "keybits")
    try:
        key_length = int(raw_key) if raw_key is not None else None
    except (TypeError, ValueError):
        key_length = None

    issues = []
    if valid_to is None:
        days_left = None
        status = "INVALID"
        issues.append("no valid expiry date")
        logger.warning(
            "%s: некоректна або відсутня дата validTo (%r)", domain, raw_valid_to
        )
    else:
        days_left = (valid_to - today).days  # різниця дат -> timedelta
        if days_left < 0:
            status = "EXPIRED"
        elif days_left <= days_warning:
            status = "WARNING"
        else:
            status = "OK"

    if WEAK_SIGNATURE.search(sig_alg):
        issues.append("weak signature")
    min_key = MIN_ECDSA_KEY if ECDSA_SIGNATURE.search(sig_alg) else MIN_RSA_KEY
    if key_length is None:
        issues.append("unknown key length")
    elif key_length < min_key:
        issues.append(f"weak key < {min_key} bit")

    return CertResult(
        Domain=domain,
        Issuer=issuer,
        ValidTo=valid_to.isoformat() if valid_to else "",
        DaysLeft=days_left,
        Status=status,
        KeyLength=key_length,
        SignatureAlg=sig_alg,
        Issues="; ".join(issues),
    )


def load_certificates(path: Path) -> list[dict]:
    """Прочитати JSON-масив сертифікатів; помилки -> ValueError з поясненням."""
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except FileNotFoundError as error:
        raise ValueError(f"файл не знайдено: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"некоректний JSON у {path}: {error}") from error
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ValueError(f"{path} має містити JSON-масив об'єктів")
    return data


def save_report(results: list[CertResult], path: Path, fmt: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(result) for result in results]
    if fmt == "csv":
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
    else:
        with path.open("w", encoding="utf-8") as file:
            json.dump(rows, file, ensure_ascii=False, indent=2)


def print_table(results: list[CertResult], issuers: Counter) -> None:
    print("=== Certificate Expiry & Safety Status ===")
    header = f"{'Domain':<30} {'Issuer':<14} {'Days Left':>10}  {'Status':<8} {'Key':>5}  Signature Alg"
    print(header)
    print("-" * (len(header) + 12))
    for r in results:
        days = f"{r.DaysLeft} days" if r.DaysLeft is not None else "-"
        alg = r.SignatureAlg + (" (WEAK)" if "weak signature" in r.Issues else "")
        key = f"{r.KeyLength}" if r.KeyLength is not None else "?"
        if "weak key" in r.Issues:
            key += "!"
        print(
            f"{r.Domain:<30} {r.Issuer:<14} {days:>10}  {r.Status:<8} {key:>5}  {alg}"
        )
    print("\n=== Issuer Statistics ===")
    for issuer, count in issuers.most_common():
        print(f"{issuer:<14} : {count}")
    print()


def analyze_ssl_certificates(
    certs_file: Path, days_warning: int, output_file: Path, fmt: str
) -> int:
    """Проаналізувати сертифікати; повертає код завершення (0 — успіх)."""
    logger.info("Loading SSL certificates data from %s...", certs_file)
    try:
        certs = load_certificates(certs_file)
    except ValueError as error:
        logger.error("%s", error)
        return 1

    today = datetime.now(timezone.utc).date()
    results = [evaluate(cert, today, days_warning) for cert in certs]
    issuers = Counter(r.Issuer for r in results)
    logger.info("Audited %d domain certificates (date: %s UTC).", len(results), today)
    print_table(results, issuers)

    expired = sum(r.Status == "EXPIRED" for r in results)
    expiring = sum(r.Status == "WARNING" for r in results)
    weak = [r for r in results if "weak" in r.Issues]
    if expired or expiring:
        logger.warning(
            "%d certificate(s) EXPIRED! %d certificate(s) expiring within %d days!",
            expired,
            expiring,
            days_warning,
        )
    for r in weak:
        logger.warning("%s: %s", r.Domain, r.Issues)

    try:
        save_report(results, output_file, fmt)
    except OSError as error:
        logger.error("Не вдалося зберегти звіт %s: %s", output_file, error)
        return 1
    logger.info("Report saved to %s", output_file)
    return 0


def non_negative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("значення має бути >= 0")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m labs.lab02.main analyze",
        description="Монітор термінів дії SSL/TLS сертифікатів (варіант 10)",
    )
    parser.add_argument(
        "--certs-data",
        type=Path,
        default=DEFAULT_CERTS,
        help="JSON-файл із даними сертифікатів",
    )
    parser.add_argument(
        "--days-warning",
        type=non_negative_int,
        default=30,
        help="поріг попередження, днів (типово 30)",
    )
    parser.add_argument(
        "--output-report", type=Path, default=DEFAULT_REPORT, help="шлях до файлу звіту"
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="формат звіту (типово csv)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    args = build_parser().parse_args(argv)
    return analyze_ssl_certificates(
        args.certs_data, args.days_warning, args.output_report, args.format
    )


if __name__ == "__main__":
    raise SystemExit(main())
