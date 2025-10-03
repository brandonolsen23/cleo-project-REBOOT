#!/usr/bin/env python3
"""
Apply City Fixes Using Bulk SQL UPDATE
Faster approach using SQL CASE statement for bulk updates.
"""

import os
import sys
from collections import defaultdict

import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.address import hash_address_raw
from common.address_parser import parse_and_validate_city
from common.db import connect_with_service_role
from psycopg2.extras import RealDictCursor


def main():
    print("=" * 70)
    print("APPLYING CITY FIXES - BULK SQL APPROACH")
    print("=" * 70)
    print()

    # Connect
    conn = connect_with_service_role()
    print("✅ Connected to database\n")

    # Load properties
    print("Loading properties...")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, address_line1, city, address_canonical, province
            FROM properties
        """)
        properties = cur.fetchall()

    print(f"✅ Loaded {len(properties):,} properties\n")

    # Build fix mappings
    print("Analyzing fixes...")
    fixes = {}
    stats = defaultdict(int)

    for i, prop in enumerate(properties):
        if i % 1000 == 0 and i > 0:
            print(f"  Progress: {i:,} / {len(properties):,}")

        fixed_city = parse_and_validate_city(
            address=prop['address_line1'] or "",
            city_raw=prop['city'] or "",
            province=prop['province'] or "ON",
            canonical=prop['address_canonical']
        )

        if fixed_city and fixed_city != prop['city']:
            new_hash = hash_address_raw(prop['address_line1'], fixed_city)
            fixes[prop['id']] = (fixed_city, new_hash)
            stats[f"{prop['city']} → {fixed_city}"] += 1

    print(f"\n✅ Found {len(fixes):,} properties to fix\n")

    if not fixes:
        print("No fixes needed!")
        return

    # Show top changes
    print("Top 10 changes:")
    for change, count in sorted(stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {change}: {count:,}")
    print()

    # Apply fixes in smaller chunks
    print("Applying fixes in chunks...")
    chunk_size = 1000
    prop_ids = list(fixes.keys())
    total_updated = 0

    with conn.cursor() as cur:
        for chunk_start in range(0, len(prop_ids), chunk_size):
            chunk_ids = prop_ids[chunk_start:chunk_start + chunk_size]

            # Build VALUES for this chunk
            values = []
            for prop_id in chunk_ids:
                city, hash_val = fixes[prop_id]
                values.append(f"('{prop_id}'::uuid, '{city}', '{hash_val}')")

            values_sql = ",\n".join(values)

            # Single UPDATE with JOIN
            sql = f"""
                WITH updates(id, new_city, new_hash) AS (
                    VALUES {values_sql}
                )
                UPDATE properties p
                SET
                    city = u.new_city,
                    address_hash_raw = u.new_hash,
                    updated_at = NOW()
                FROM updates u
                WHERE p.id = u.id
            """

            cur.execute(sql)
            total_updated += cur.rowcount
            conn.commit()

            print(f"  Updated {total_updated:,} / {len(fixes):,} properties")

    print(f"\n✅ SUCCESS: Updated {total_updated:,} properties!\n")

    conn.close()


if __name__ == "__main__":
    main()
