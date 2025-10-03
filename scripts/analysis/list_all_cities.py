#!/usr/bin/env python3
"""
List all unique city values from the database
to help expand the valid cities list.
"""

import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.db import connect_with_service_role
from common.ontario_cities import is_valid_city, is_likely_unit_or_address


def main():
    conn = connect_with_service_role()

    with conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get all unique cities with counts
            cur.execute("""
                SELECT
                    city,
                    COUNT(*) as count
                FROM properties
                WHERE city IS NOT NULL
                GROUP BY city
                ORDER BY count DESC
            """)

            cities = cur.fetchall()

    conn.close()

    print(f"Found {len(cities)} unique city values\n")
    print("=" * 80)
    print(f"{'City Name':<40} {'Count':<10} {'Valid?':<10} {'Issue?'}")
    print("=" * 80)

    for city_row in cities[:100]:  # Top 100
        city = city_row['city']
        count = city_row['count']
        is_valid = "✅ YES" if is_valid_city(city) else "❌ NO"
        is_issue = "⚠️ UNIT/ADDR" if is_likely_unit_or_address(city) else ""

        print(f"{city:<40} {count:<10} {is_valid:<10} {is_issue}")


if __name__ == "__main__":
    main()
