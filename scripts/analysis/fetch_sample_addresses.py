#!/usr/bin/env python3
"""
Fetch sample addresses from database for libpostal testing.
"""

import os
import psycopg2
import json

# Database connection
DATABASE_URL = os.environ.get('DATABASE_URL')

def fetch_sample_addresses():
    """Fetch 10 sample addresses from database (5 from transactions, 5 from brand_locations)"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("=" * 80)
    print("SAMPLE ADDRESSES FROM TRANSACTIONS (RealTrack)")
    print("=" * 80)

    # Fetch from transactions
    cur.execute("""
        SELECT address_raw, city_raw, address_canonical
        FROM transactions
        WHERE address_raw IS NOT NULL AND city_raw IS NOT NULL
        LIMIT 5
    """)

    tx_addresses = []
    for row in cur.fetchall():
        address_raw, city_raw, canonical = row
        tx_addresses.append({
            'source': 'transactions',
            'address_raw': address_raw,
            'city_raw': city_raw,
            'canonical': canonical
        })
        print(f"\nAddress: {address_raw}")
        print(f"City: {city_raw}")
        print(f"Canonical: {canonical}")
        print("-" * 80)

    print("\n" + "=" * 80)
    print("SAMPLE ADDRESSES FROM BRAND_LOCATIONS")
    print("=" * 80)

    # Fetch from brand_locations
    cur.execute("""
        SELECT address_line1, city, postal_code
        FROM brand_locations
        WHERE address_line1 IS NOT NULL AND city IS NOT NULL
        LIMIT 5
    """)

    brand_addresses = []
    for row in cur.fetchall():
        address, city, postal_code = row
        brand_addresses.append({
            'source': 'brand_locations',
            'address': address,
            'city': city,
            'postal_code': postal_code
        })
        print(f"\nAddress: {address}")
        print(f"City: {city}")
        print(f"Postal Code: {postal_code}")
        print("-" * 80)

    cur.close()
    conn.close()

    # Save to JSON for test script
    all_addresses = tx_addresses + brand_addresses
    with open('/tmp/sample_addresses.json', 'w') as f:
        json.dump(all_addresses, f, indent=2)

    print(f"\n✅ Saved {len(all_addresses)} sample addresses to /tmp/sample_addresses.json")

    return all_addresses

if __name__ == '__main__':
    fetch_sample_addresses()
