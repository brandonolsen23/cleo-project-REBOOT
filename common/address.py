import hashlib
import re


_SPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^A-Z0-9 ]+")


def normalize_raw_address(address: str | None, city: str | None) -> str:
    """Minimal normalization for ingest-time raw address hashing.

    - Uppercase
    - Remove punctuation except spaces
    - Collapse multiple spaces
    - Join address + city
    """
    parts = []
    if address:
        parts.append(str(address))
    if city:
        parts.append(str(city))
    s = " ".join(parts).strip().upper()
    s = _PUNCT_RE.sub(" ", s)
    s = _SPACE_RE.sub(" ", s).strip()
    return s


def hash_address_raw(address: str | None, city: str | None) -> str:
    normalized = normalize_raw_address(address, city)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

