#!/usr/bin/env python3
"""
Extract Ontario Cities from NAR 2024 Address Database
Reads the GeoParquet file and generates a comprehensive Ontario cities reference list.

This script:
1. Queries the NAR address database for all Ontario cities
2. Analyzes the results and shows statistics
3. Generates an updated ontario_cities.py with complete coverage
4. Compares before/after to show improvement

Date: 2025-10-03
"""

import os
import sys
from collections import defaultdict

import duckdb

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.ontario_cities import VALID_ONTARIO_CITIES


def extract_ontario_cities():
    """Extract all unique cities from NAR database for Ontario."""

    print("=" * 70)
    print("EXTRACTING ONTARIO CITIES FROM NAR 2024 DATABASE")
    print("=" * 70)
    print()

    # Path to parquet file
    parquet_path = "data/nar/addresses.geo.parquet"

    if not os.path.exists(parquet_path):
        print(f"❌ Parquet file not found: {parquet_path}")
        print("   Please ensure addresses.geo.parquet is in data/nar/")
        sys.exit(1)

    print(f"📁 Reading from: {parquet_path}")
    print(f"📏 File size: {os.path.getsize(parquet_path) / (1024**3):.2f} GB\n")

    # Connect to DuckDB (in-memory)
    print("🔌 Connecting to DuckDB...")
    con = duckdb.connect()
    print("✅ Connected\n")

    # Query 1: Count total Canadian addresses
    print("1️⃣  Counting total Canadian addresses...")
    result = con.execute(f"""
        SELECT COUNT(*) as total
        FROM read_parquet('{parquet_path}')
        WHERE country = 'CA'
    """).fetchone()
    total_ca = result[0]
    print(f"   📊 Total Canadian addresses: {total_ca:,}\n")

    # Query 2: Count Ontario addresses
    print("2️⃣  Counting Ontario addresses...")
    result = con.execute(f"""
        SELECT COUNT(*) as total
        FROM read_parquet('{parquet_path}')
        WHERE country = 'CA' AND state = 'ON'
    """).fetchone()
    total_on = result[0]
    print(f"   📊 Total Ontario addresses: {total_on:,}\n")

    # Query 3: Extract all unique Ontario cities with counts
    print("3️⃣  Extracting unique Ontario cities (this may take a few minutes)...")
    cities_data = con.execute(f"""
        SELECT
            city,
            COUNT(*) as address_count
        FROM read_parquet('{parquet_path}')
        WHERE country = 'CA'
          AND state = 'ON'
          AND city IS NOT NULL
          AND city != ''
        GROUP BY city
        ORDER BY address_count DESC
    """).fetchall()

    print(f"✅ Found {len(cities_data):,} unique cities in Ontario\n")

    # Analyze results
    print("4️⃣  Analyzing city data...")

    # Normalize city names (uppercase for comparison)
    nar_cities = {}
    for city, count in cities_data:
        city_upper = city.strip().upper()
        if city_upper in nar_cities:
            nar_cities[city_upper] += count
        else:
            nar_cities[city_upper] = count

    print(f"   📊 Unique cities (normalized): {len(nar_cities):,}")
    print(f"   📊 Current reference list: {len(VALID_ONTARIO_CITIES):,} cities\n")

    # Compare with current list
    print("5️⃣  Comparing with current reference list...")

    in_both = set(nar_cities.keys()) & VALID_ONTARIO_CITIES
    only_in_nar = set(nar_cities.keys()) - VALID_ONTARIO_CITIES
    only_in_current = VALID_ONTARIO_CITIES - set(nar_cities.keys())

    print(f"   ✅ Cities in both: {len(in_both):,}")
    print(f"   🆕 Cities only in NAR: {len(only_in_nar):,}")
    print(f"   ⚠️  Cities only in current list: {len(only_in_current):,}\n")

    # Show top 20 cities by address count
    print("6️⃣  Top 20 Ontario cities by address count:")
    sorted_cities = sorted(nar_cities.items(), key=lambda x: x[1], reverse=True)
    for i, (city, count) in enumerate(sorted_cities[:20], 1):
        in_current = "✅" if city in VALID_ONTARIO_CITIES else "🆕"
        print(f"   {i:2d}. {in_current} {city:<30s} {count:>8,} addresses")
    print()

    # Show sample of new cities
    print("7️⃣  Sample of NEW cities found in NAR (top 30 by address count):")
    new_cities_sorted = [(c, count) for c, count in sorted_cities if c in only_in_nar]
    for city, count in new_cities_sorted[:30]:
        print(f"      • {city:<30s} ({count:,} addresses)")
    if len(new_cities_sorted) > 30:
        print(f"      ... and {len(new_cities_sorted) - 30:,} more")
    print()

    # Generate updated cities list
    print("8️⃣  Generating updated ontario_cities.py...")

    # Filter cities with reasonable address counts (at least 5 addresses)
    filtered_cities = {city for city, count in nar_cities.items() if count >= 5}

    print(f"   📊 Cities with ≥5 addresses: {len(filtered_cities):,}")
    print(f"   📊 Filtered out: {len(nar_cities) - len(filtered_cities):,} (too few addresses)\n")

    # Save to new file
    output_file = "common/ontario_cities_nar.py"
    generate_cities_file(filtered_cities, sorted_cities, output_file)

    print(f"✅ Generated: {output_file}\n")

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"📊 Statistics:")
    print(f"   Ontario addresses in NAR:     {total_on:,}")
    print(f"   Unique cities found:          {len(nar_cities):,}")
    print(f"   Cities (≥5 addresses):        {len(filtered_cities):,}")
    print()
    print(f"📈 Coverage Improvement:")
    print(f"   Before (manual list):         {len(VALID_ONTARIO_CITIES):,} cities")
    print(f"   After (NAR-based):            {len(filtered_cities):,} cities")
    print(f"   Improvement:                  +{len(filtered_cities) - len(VALID_ONTARIO_CITIES):,} cities")
    print()
    print(f"🆕 New cities that will be recognized:")
    print(f"   Previously invalid:           {len(only_in_nar):,} cities")
    print(f"   Now valid (≥5 addresses):     {len([c for c in only_in_nar if nar_cities[c] >= 5]):,} cities")
    print()
    print("=" * 70)
    print()
    print("NEXT STEPS:")
    print("=" * 70)
    print()
    print("1. Review the generated file: common/ontario_cities_nar.py")
    print("2. Replace common/ontario_cities.py with the NAR version:")
    print("   mv common/ontario_cities_nar.py common/ontario_cities.py")
    print("3. Re-run validation to see improvement:")
    print("   python3 scripts/analysis/validate_city_fixes.py")
    print()

    con.close()

    return filtered_cities, nar_cities


def generate_cities_file(cities_set, sorted_cities, output_file):
    """Generate the ontario_cities.py file with NAR data."""

    # Keep the existing amalgamation mappings and helper functions
    # Just update the VALID_ONTARIO_CITIES set

    with open(output_file, 'w') as f:
        f.write('"""\n')
        f.write('Ontario Cities Reference List (Generated from NAR 2024)\n')
        f.write('This module provides a comprehensive list of valid Ontario cities,\n')
        f.write('extracted from Statistics Canada National Address Register 2024.\n')
        f.write('"""\n\n')

        f.write('# Valid Ontario cities and municipalities\n')
        f.write(f'# Source: NAR 2024 - {len(cities_set):,} cities with ≥5 addresses\n')
        f.write('# Generated: 2025-10-03\n')
        f.write('VALID_ONTARIO_CITIES = {\n')

        # Sort cities alphabetically
        for city in sorted(cities_set):
            f.write(f'    "{city}",\n')

        f.write('}\n\n')

        # Copy the amalgamation mappings from original file
        f.write("""
# Amalgamated cities mapping
# Maps old municipality names to current amalgamated city
AMALGAMATED_CITIES = {
    # Toronto amalgamation (1998)
    "SCARBOROUGH": "TORONTO",
    "ETOBICOKE": "TORONTO",
    "NORTH YORK": "TORONTO",
    "YORK": "TORONTO",
    "EAST YORK": "TORONTO",

    # Hamilton amalgamation (2001)
    "ANCASTER": "HAMILTON",
    "DUNDAS": "HAMILTON",
    "FLAMBOROUGH": "HAMILTON",
    "STONEY CREEK": "HAMILTON",
    "GLANBROOK": "HAMILTON",

    # Ottawa amalgamation (2001)
    "NEPEAN": "OTTAWA",
    "KANATA": "OTTAWA",
    "GLOUCESTER": "OTTAWA",
    "VANIER": "OTTAWA",
    "CUMBERLAND": "OTTAWA",
    "OSGOODE": "OTTAWA",
    "RIDEAU": "OTTAWA",
    "WEST CARLETON": "OTTAWA",
    "GOULBOURN": "OTTAWA",

    # Common variations/aliases
    "GEORGTOWN": "GEORGETOWN",  # Typo
    "STOUFVILLE": "STOUFFVILLE",  # Typo
    "N. YORK": "NORTH YORK",  # Abbreviation
    "E. YORK": "EAST YORK",  # Abbreviation
}


# Sub-municipality patterns that should be removed
SUB_MUNICIPALITY_SUFFIXES = [
    "(SCARBOROUGH)",
    "(ETOBICOKE)",
    "(NORTH YORK)",
    "(YORK)",
    "(EAST YORK)",
    "(ANCASTER)",
    "(DUNDAS)",
    "(FLAMBOROUGH)",
    "(STONEY CREEK)",
    "(GLANBROOK)",
    "(GEORGETOWN)",
    "(ALCONA)",
    "(COOKSTOWN)",
    "(ALLISTON)",
    "(OLD TORONTO)",
    "(NEPEAN)",
    "(GLOUCESTER)",
    "(KANATA)",
]


def normalize_city(city: str | None) -> str | None:
    \"\"\"
    Normalize a city name to its canonical form.

    - Uppercases
    - Removes sub-municipality suffixes like "(Scarborough)"
    - Maps amalgamated cities to current name
    - Returns None if city is None or empty

    Args:
        city: Raw city string from source data

    Returns:
        Normalized city name, or None if invalid
    \"\"\"
    if not city:
        return None

    # Uppercase
    city_upper = city.strip().upper()

    # Remove sub-municipality suffixes
    for suffix in SUB_MUNICIPALITY_SUFFIXES:
        if suffix in city_upper:
            city_upper = city_upper.replace(suffix, "").strip()

    # Map amalgamated cities
    city_upper = AMALGAMATED_CITIES.get(city_upper, city_upper)

    return city_upper if city_upper else None


def is_valid_city(city: str | None) -> bool:
    \"\"\"
    Check if a city name is in the valid Ontario cities list.

    Args:
        city: City name to validate (will be normalized first)

    Returns:
        True if city is valid, False otherwise
    \"\"\"
    if not city:
        return False

    normalized = normalize_city(city)
    return normalized in VALID_ONTARIO_CITIES


def is_likely_unit_or_address(city: str | None) -> bool:
    \"\"\"
    Check if a "city" value actually contains unit numbers or address components.

    Args:
        city: Value from city field

    Returns:
        True if this looks like a unit/suite/address, not a city
    \"\"\"
    if not city:
        return False

    city_upper = city.strip().upper()

    # Check for unit/suite indicators
    unit_patterns = [
        r'\\bUNIT\\b',
        r'\\bSUITE\\b',
        r'\\bAPT\\b',
        r'\\bAPARTMENT\\b',
        r'#\\d+',  # Matches #42, #123, etc.
        r'\\bUNIT\\s*#',
        r'\\bSUITE\\s*#',
    ]

    import re
    for pattern in unit_patterns:
        if re.search(pattern, city_upper):
            return True

    # Check for street address indicators
    address_patterns = [
        r'\\bSTREET\\b',
        r'\\bROAD\\b',
        r'\\bAVENUE\\b',
        r'\\bBOULEVARD\\b',
        r'\\bBLVD\\b',
        r'\\bDRIVE\\b',
        r'\\bLANE\\b',
        r'\\bCOURT\\b',
        r'\\bCRESCENT\\b',
        r'\\bCRES\\b',
        r'\\bPLACE\\b',
        r'\\bTRAIL\\b',
        r'\\bWAY\\b',
        r'\\bCIRCLE\\b',
        r'\\bPKWY\\b',
        r'\\bPARKWAY\\b',
        r'\\bHWY\\b',
        r'\\bHIGHWAY\\b',
    ]

    for pattern in address_patterns:
        if re.search(pattern, city_upper):
            return True

    # Check if starts with a number (likely street number)
    if re.match(r'^\\d+', city_upper):
        return True

    return False


def extract_city_from_canonical(canonical: str | None) -> str | None:
    \"\"\"
    Extract city from a canonical address string.

    Expected format: "STREET ADDRESS, CITY, PROVINCE, COUNTRY"
    Example: "9025 AIRPORT ROAD, UNIT 1, BRAMPTON, CA"

    Args:
        canonical: Canonical address string

    Returns:
        Extracted city name, or None if not found
    \"\"\"
    if not canonical:
        return None

    # Split by comma
    parts = [p.strip() for p in canonical.split(',')]

    if len(parts) < 3:
        return None

    # Check if second-to-last part is a province (ON, ONTARIO)
    potential_province = parts[-2].upper()
    if potential_province in ('ON', 'ONTARIO'):
        # City is the part before province
        city_idx = -3
        if len(parts) > abs(city_idx):
            city = parts[city_idx].strip()
            # Validate it's actually a city
            if is_valid_city(city):
                return normalize_city(city)

    # Try second-to-last part as city (for "STREET, CITY, COUNTRY" format)
    if len(parts) >= 3:
        city = parts[-2].strip()
        if is_valid_city(city):
            return normalize_city(city)

    # Look for any valid city in the parts
    for part in parts[1:]:  # Skip first part (street address)
        part_clean = part.strip()
        if is_valid_city(part_clean):
            return normalize_city(part_clean)

    return None
""")

    print(f"   ✅ Wrote {len(cities_set):,} cities to {output_file}")


if __name__ == "__main__":
    extract_ontario_cities()
