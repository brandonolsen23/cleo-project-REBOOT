import hashlib
import json
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation


PRICE_RE = re.compile(r"[^0-9.]")


def canonical_price(value: str | None) -> Decimal | None:
    if not value:
        return None
    cleaned = PRICE_RE.sub("", value)
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def parse_date(value: str | None):
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d %b %Y", "%Y-%m-%d", "%d %B %Y"):  # e.g., 10 Apr 2025
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_site_area(value: str | None) -> tuple[Optional[Decimal], Optional[Decimal]]:
    """Parse strings like '0.30 acre', '0.32 acres', '13,000 sf', '13000 sqft'.

    Returns (acres, sqft) where either may be None when not derivable.
    """
    if not value:
        return (None, None)
    s = value.strip().lower()
    # remove commas
    s = s.replace(",", "")
    try:
        if "acre" in s:
            num = Decimal(re.findall(r"[0-9]*\.?[0-9]+", s)[0])
            acres = num
            sqft = (acres * Decimal("43560")).quantize(Decimal("1."))
            return (acres, sqft)
        if "sf" in s or "sqft" in s or "square foot" in s or "square feet" in s:
            num = Decimal(re.findall(r"[0-9]*\.?[0-9]+", s)[0])
            sqft = num
            acres = (sqft / Decimal("43560")).quantize(Decimal("0.0001"))
            return (acres, sqft)
    except Exception:
        return (None, None)
    return (None, None)


def compute_source_hash(record: dict) -> str:
    # Use key fields that are stable across runs
    parts = [
        (record.get("ARN") or "").strip().upper(),
        (record.get("PIN") or "").strip().upper(),
        (record.get("Address") or "").strip().upper(),
        (record.get("City") or "").strip().upper(),
        (record.get("SaleDate") or "").strip().upper(),
        (record.get("SalePrice") or "").strip().upper(),
    ]
    payload = "|".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def to_jsonb(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
