import hashlib
import re
from typing import Optional


_SPACE_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^A-Z0-9 ]+")


def canonicalize_address(address_line1: Optional[str], city: Optional[str], province: Optional[str], country: Optional[str] = "CA") -> str:
    parts = []
    if address_line1:
        parts.append(address_line1)
    if city:
        parts.append(city)
    if province:
        parts.append(province)
    if country:
        parts.append(country)
    s = ", ".join(parts).strip().upper()
    # simplify for hashing
    s2 = _PUNCT_RE.sub(" ", s)
    s2 = _SPACE_RE.sub(" ", s2).strip()
    return s


def hash_canonical_address(address_line1: Optional[str], city: Optional[str], province: Optional[str], country: Optional[str] = "CA") -> str:
    # Hash over simplified normalized string to get a stable key
    parts = []
    if address_line1:
        parts.append(address_line1)
    if city:
        parts.append(city)
    if province:
        parts.append(province)
    if country:
        parts.append(country)
    s = " ".join(parts).strip().upper()
    s = _PUNCT_RE.sub(" ", s)
    s = _SPACE_RE.sub(" ", s).strip()
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

