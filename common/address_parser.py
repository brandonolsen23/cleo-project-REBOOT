"""
Address Parser for Canadian Addresses
Provides robust parsing and validation of address components,
with special handling for Ontario addresses.
"""

import re
from dataclasses import dataclass
from typing import Optional

from .ontario_cities import (
    extract_city_from_canonical,
    is_likely_unit_or_address,
    is_valid_city,
    normalize_city,
)


@dataclass
class ParsedAddress:
    """Result of address parsing operation."""
    street_address: str
    city: Optional[str]
    province: Optional[str]
    unit_number: Optional[str] = None
    warnings: list[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def extract_unit_number(address: str) -> tuple[str, Optional[str]]:
    """
    Extract unit number from address string.

    Args:
        address: Full address string

    Returns:
        Tuple of (address_without_unit, unit_number)
    """
    if not address:
        return address, None

    address_upper = address.upper()

    # Patterns to match unit numbers
    unit_patterns = [
        r'\bUNIT\s*#?(\d+[A-Z]?)',
        r'\bSUITE\s*#?(\d+[A-Z]?)',
        r'\bAPT\.?\s*#?(\d+[A-Z]?)',
        r'\bAPARTMENT\s*#?(\d+[A-Z]?)',
        r'#\s*(\d+[A-Z]?)\b',
        r'\bU\s*(\d+[A-Z]?)\b',  # "U 101"
    ]

    for pattern in unit_patterns:
        match = re.search(pattern, address_upper)
        if match:
            unit_num = match.group(1)
            # Remove the unit portion from the address
            address_clean = re.sub(pattern, '', address, flags=re.IGNORECASE).strip()
            # Clean up any double spaces
            address_clean = re.sub(r'\s+', ' ', address_clean).strip()
            # Remove trailing commas
            address_clean = address_clean.rstrip(',').strip()
            return address_clean, unit_num

    return address, None


def parse_and_validate_city(
    address: str,
    city_raw: str,
    province: str = "ON",
    canonical: Optional[str] = None
) -> Optional[str]:
    """
    Parse and validate city from raw inputs.

    This function implements the safe normalization strategy:
    1. If city_raw is valid → use it (normalized)
    2. If city_raw is garbage (unit/address) → try to extract from canonical
    3. If canonical extraction fails → return None with warning

    Args:
        address: Street address
        city_raw: City field from source (may be garbage)
        province: Province code (default: ON)
        canonical: Canonical address if available

    Returns:
        Validated and normalized city name, or None if invalid
    """
    warnings = []

    # Step 1: Check if city_raw is obviously wrong (unit/address)
    if is_likely_unit_or_address(city_raw):
        warnings.append(f"City field contains unit/address: '{city_raw}'")

        # Try to extract from canonical
        if canonical:
            extracted_city = extract_city_from_canonical(canonical)
            if extracted_city:
                return extracted_city
            else:
                warnings.append("Could not extract city from canonical address")
        else:
            warnings.append("No canonical address available for extraction")

        return None

    # Step 2: Normalize and validate city_raw
    normalized = normalize_city(city_raw)

    if normalized and is_valid_city(normalized):
        return normalized

    # Step 3: city_raw doesn't match known cities, try canonical
    if canonical:
        extracted_city = extract_city_from_canonical(canonical)
        if extracted_city:
            warnings.append(f"Used canonical address to correct city from '{city_raw}' to '{extracted_city}'")
            return extracted_city

    # Step 4: All methods failed
    if city_raw:
        warnings.append(f"Invalid city name: '{city_raw}'")

    return None


def parse_canadian_address(
    address: str,
    city: str,
    province: str = "ON",
    canonical: Optional[str] = None
) -> ParsedAddress:
    """
    Parse and validate Canadian address components.

    This is the main entry point for address parsing.

    Args:
        address: Street address from source
        city: City field from source (may be garbage)
        province: Province code (default: ON)
        canonical: Canonical address if available

    Returns:
        ParsedAddress with validated components and warnings
    """
    warnings = []

    # Extract unit number from address
    address_clean, unit_num = extract_unit_number(address)

    # Parse and validate city
    validated_city = parse_and_validate_city(
        address=address,
        city_raw=city,
        province=province,
        canonical=canonical
    )

    if not validated_city:
        if is_likely_unit_or_address(city):
            warnings.append(f"City field contains unit/address: '{city}'")
        else:
            warnings.append(f"Could not validate city: '{city}'")

    return ParsedAddress(
        street_address=address_clean,
        city=validated_city,
        province=province,
        unit_number=unit_num,
        warnings=warnings
    )


def build_canonical_address(
    address: str,
    city: str,
    province: str = "ON",
    country: str = "CA"
) -> str:
    """
    Build canonical address string from components.

    Format: "STREET ADDRESS, CITY, PROVINCE, COUNTRY"

    Args:
        address: Street address
        city: City name
        province: Province code
        country: Country code

    Returns:
        Canonical address string
    """
    parts = []

    if address:
        parts.append(address.strip().upper())

    if city:
        parts.append(city.strip().upper())

    if province:
        parts.append(province.strip().upper())

    if country:
        parts.append(country.strip().upper())

    return ", ".join(parts)
