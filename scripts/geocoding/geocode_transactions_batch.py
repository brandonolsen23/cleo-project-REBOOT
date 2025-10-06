"""
Geocode transaction addresses using Google Geocoding API
Stores results in google_geocoded_addresses table
"""
import os
import sys
import time
import psycopg2
from psycopg2.extras import Json

# Add project root to path
sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')
from common.google_geocoder import GoogleGeocoder


def geocode_transactions_batch(limit=100):
    """Geocode a batch of transaction addresses"""

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()
    geocoder = GoogleGeocoder()

    if not geocoder.available():
        print("❌ Google API key not found!")
        return

    print(f"Starting geocoding of {limit} transaction addresses...")
    print("=" * 100)

    # Get transactions that haven't been geocoded yet
    cur.execute("""
        SELECT t.id, t.address_raw, t.city_raw, t.property_id
        FROM transactions t
        LEFT JOIN google_geocoded_addresses g
            ON g.source_table = 'transactions' AND g.source_id = t.id
        WHERE g.id IS NULL
            AND t.address_raw IS NOT NULL
        ORDER BY t.created_at DESC
        LIMIT %s
    """, (limit,))

    transactions = cur.fetchall()
    total = len(transactions)

    print(f"Found {total} transactions to geocode\n")

    success_count = 0
    failure_count = 0
    ontario_count = 0

    for i, (tx_id, address_raw, city_raw, property_id) in enumerate(transactions, 1):
        # Build full address
        input_address = f"{address_raw}, {city_raw}" if city_raw else address_raw

        print(f"[{i}/{total}] {input_address[:70]}")

        # Geocode with Google
        result = geocoder.geocode(input_address)

        if result:
            components = result.get('components', {})
            location = result.get('location', {})

            # Insert successful result
            cur.execute("""
                INSERT INTO google_geocoded_addresses (
                    source_table,
                    source_id,
                    input_address,
                    google_formatted_address,
                    google_street_number,
                    google_street,
                    google_city,
                    google_province,
                    google_postal_code,
                    google_latitude,
                    google_longitude,
                    google_place_id,
                    google_confidence,
                    geocode_success,
                    google_raw_response
                ) VALUES (
                    'transactions',
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                tx_id,
                input_address,
                result.get('formatted_address'),
                components.get('street_number'),
                components.get('street'),
                components.get('city'),
                components.get('province'),
                components.get('postal_code'),
                location.get('lat'),
                location.get('lng'),
                result.get('place_id'),
                result.get('confidence'),
                True,
                Json(result.get('raw'))
            ))

            province = components.get('province', '')
            print(f"  ✓ {result.get('formatted_address')[:60]}")
            print(f"    {components.get('city')}, {province} {components.get('postal_code')}")

            success_count += 1
            if province == 'ON':
                ontario_count += 1
        else:
            # Insert failure
            cur.execute("""
                INSERT INTO google_geocoded_addresses (
                    source_table,
                    source_id,
                    input_address,
                    geocode_success,
                    geocode_error
                ) VALUES (
                    'transactions', %s, %s, %s, %s
                )
            """, (
                tx_id,
                input_address,
                False,
                'No result from Google API'
            ))

            print(f"  ✗ FAILED")
            failure_count += 1

        conn.commit()

        # Rate limiting - be polite to Google
        if i % 10 == 0:
            time.sleep(1)

    print("\n" + "=" * 100)
    print("BATCH COMPLETE")
    print("=" * 100)
    print(f"Total processed: {total}")
    print(f"Successful: {success_count} ({success_count*100/total:.1f}%)")
    print(f"Failed: {failure_count} ({failure_count*100/total:.1f}%)")
    print(f"Ontario addresses: {ontario_count} ({ontario_count*100/total:.1f}%)")
    print(f"With postal codes: {success_count} ({success_count*100/total:.1f}%)")

    cur.close()
    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Geocode transaction addresses')
    parser.add_argument('--limit', type=int, default=100, help='Number of addresses to geocode')
    args = parser.parse_args()

    geocode_transactions_batch(args.limit)
