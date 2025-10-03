#!/usr/bin/env python3
"""
Validate City Fixes
Verifies that city corrections were applied successfully and data quality improved.
"""

import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.db import connect_with_service_role
from common.ontario_cities import is_likely_unit_or_address, is_valid_city


def main():
    print("=" * 70)
    print("VALIDATION: City Fix Results")
    print("=" * 70)
    print()

    conn = connect_with_service_role()
    print("✅ Connected to database\n")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Test 1: Count properties with unit/suite in city field
        print("1️⃣  Checking for unit/suite indicators in city field...")
        cur.execute("""
            SELECT COUNT(*) as count
            FROM properties
            WHERE city ~* '\\b(unit|suite|#\\d+|apt|apartment)\\b'
        """)
        result = cur.fetchone()
        unit_count = result['count']
        if unit_count == 0:
            print(f"   ✅ PASS: No unit/suite indicators found in city field\n")
        else:
            print(f"   ⚠️  WARNING: {unit_count:,} properties still have unit/suite in city\n")

        # Test 2: Count properties with street indicators in city field
        print("2️⃣  Checking for street addresses in city field...")
        cur.execute("""
            SELECT COUNT(*) as count
            FROM properties
            WHERE city ~* '(street|road|avenue|blvd|boulevard|drive|lane|court)\\b'
        """)
        result = cur.fetchone()
        street_count = result['count']
        if street_count == 0:
            print(f"   ✅ PASS: No street addresses found in city field\n")
        else:
            print(f"   ⚠️  WARNING: {street_count:,} properties have street addresses in city\n")

        # Test 3: Check unique city count
        print("3️⃣  Counting unique city values...")
        cur.execute("""
            SELECT COUNT(DISTINCT city) as count
            FROM properties
            WHERE city IS NOT NULL
        """)
        result = cur.fetchone()
        unique_cities = result['count']
        print(f"   📊 Unique cities: {unique_cities:,}")
        if unique_cities < 250:
            print(f"   ✅ GOOD: Reasonable number of unique cities\n")
        else:
            print(f"   ⚠️  Many unique cities (expected ~60-150 for ON)\n")

        # Test 4: Top 20 cities
        print("4️⃣  Top 20 cities by property count...")
        cur.execute("""
            SELECT
                city,
                COUNT(*) as count
            FROM properties
            WHERE city IS NOT NULL
            GROUP BY city
            ORDER BY count DESC
            LIMIT 20
        """)
        cities = cur.fetchall()
        for city_row in cities:
            city = city_row['city']
            count = city_row['count']
            valid_indicator = "✅" if is_valid_city(city) else "❌"
            print(f"   {valid_indicator} {city:<30s} {count:>5,} properties")
        print()

        # Test 5: Check for null cities
        print("5️⃣  Checking for null/empty cities...")
        cur.execute("""
            SELECT COUNT(*) as count
            FROM properties
            WHERE city IS NULL OR city = ''
        """)
        result = cur.fetchone()
        null_count = result['count']
        print(f"   📊 Null/empty cities: {null_count:,}\n")

        # Test 6: Sample invalid cities
        print("6️⃣  Sampling invalid cities (showing up to 20)...")
        cur.execute("""
            SELECT DISTINCT city, COUNT(*) as count
            FROM properties
            WHERE city IS NOT NULL
            GROUP BY city
            ORDER BY count DESC
        """)
        all_cities = cur.fetchall()

        invalid_cities = []
        for city_row in all_cities:
            city = city_row['city']
            if not is_valid_city(city) and not is_likely_unit_or_address(city):
                invalid_cities.append(city_row)

        if invalid_cities:
            print(f"   Found {len(invalid_cities):,} cities not in reference list:")
            for city_row in invalid_cities[:20]:
                print(f"      • {city_row['city']:<30s} ({city_row['count']:,} properties)")
            if len(invalid_cities) > 20:
                print(f"      ... and {len(invalid_cities) - 20} more")
            print()
        else:
            print(f"   ✅ All cities are in the valid reference list\n")

        # Test 7: Compare before/after (using backup column)
        print("7️⃣  Comparing before/after (sample of 10 changes)...")
        cur.execute("""
            SELECT
                id,
                address_line1,
                city_backup as old_city,
                city as new_city
            FROM properties
            WHERE city_backup IS NOT NULL
              AND city != city_backup
            LIMIT 10
        """)
        changes = cur.fetchall()

        if changes:
            for change in changes:
                print(f"   '{change['old_city']}' → '{change['new_city']}'")
            print()
        else:
            print(f"   ℹ️  No changes found (city_backup == city)\n")

        # Test 8: Final summary stats
        print("8️⃣  Summary Statistics...")
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(city) as with_city,
                COUNT(city_backup) as with_backup,
                COUNT(*) FILTER (WHERE city != city_backup) as changed
            FROM properties
        """)
        stats = cur.fetchone()

        print(f"   Total properties:     {stats['total']:,}")
        print(f"   With city:            {stats['with_city']:,} ({stats['with_city']/stats['total']*100:.1f}%)")
        print(f"   With backup:          {stats['with_backup']:,}")
        print(f"   Changed:              {stats['changed']:,} ({stats['changed']/stats['total']*100:.1f}%)")
        print()

    conn.close()

    print("=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)
    print()
    print("Key Metrics:")
    print(f"  • Unit/suite in city field:  {unit_count:,}")
    print(f"  • Street addresses in city:  {street_count:,}")
    print(f"  • Unique cities:             {unique_cities:,}")
    print(f"  • Properties changed:        {stats['changed']:,}")
    print()

    if unit_count == 0 and street_count == 0:
        print("✅ SUCCESS: No obvious garbage data in city field!")
    else:
        print("⚠️  Some data quality issues remain (see details above)")
    print()


if __name__ == "__main__":
    main()
