"""
Geocode transactions with multi-property parsing
Stores results in google_geocoded_addresses and links in transaction_address_links
"""
import os
import sys
import time
import psycopg2
from psycopg2.extras import Json

sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')
from common.google_geocoder import GoogleGeocoder
from common.multi_property_parser import MultiPropertyAddressParser


def geocode_with_multi_property(limit=100):
    """Geocode transactions, handling multi-property addresses"""

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()
    geocoder = GoogleGeocoder()

    if not geocoder.available():
        print("❌ Google API key not found!")
        return

    print(f"Starting geocoding with multi-property parsing (limit: {limit})...")
    print("=" * 100)

    # Get transactions that haven't been processed yet
    # Skip transactions already in google_geocoded_addresses
    cur.execute("""
        SELECT t.id, t.address_raw, t.city_raw
        FROM transactions t
        WHERE t.address_raw IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM google_geocoded_addresses g
                WHERE g.source_table = 'transactions' AND g.source_id = t.id
            )
        ORDER BY t.created_at DESC
        LIMIT %s
    """, (limit,))

    transactions = cur.fetchall()
    total = len(transactions)

    print(f"Found {total} transactions to process\n")

    success_count = 0
    failure_count = 0
    multi_property_count = 0
    total_addresses_geocoded = 0

    for i, (tx_id, address_raw, city_raw) in enumerate(transactions, 1):
        print(f"[{i}/{total}] Processing: {address_raw}, {city_raw or 'NO CITY'}")

        # Parse for multi-property
        parsed = MultiPropertyAddressParser.parse(address_raw, city_raw)

        if parsed['is_multi_property']:
            multi_property_count += 1
            print(f"  ⚡ Multi-property ({parsed['pattern_type']}): {len(parsed['addresses'])} addresses")

        # Geocode each address
        for addr_data in parsed['addresses']:
            full_address = addr_data['full_address']

            # Add "Ontario" to improve accuracy
            geocode_input = f"{full_address}, Ontario" if city_raw else f"{full_address}, Ontario"

            print(f"    Geocoding: {geocode_input[:70]}")

            result = geocoder.geocode(geocode_input)

            geocoded_address_id = None

            if result:
                components = result.get('components', {})
                location = result.get('location', {})

                # Insert into google_geocoded_addresses
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
                    RETURNING id
                """, (
                    tx_id,
                    geocode_input,
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

                geocoded_address_id = cur.fetchone()[0]
                total_addresses_geocoded += 1

                province = components.get('province', '')
                print(f"      ✓ {components.get('city')}, {province} {components.get('postal_code')}")
                success_count += 1
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
                    RETURNING id
                """, (
                    tx_id,
                    geocode_input,
                    False,
                    'No result from Google API'
                ))

                geocoded_address_id = cur.fetchone()[0]
                print(f"      ✗ FAILED")
                failure_count += 1

            # Link transaction to geocoded address
            cur.execute("""
                INSERT INTO transaction_address_links (
                    transaction_id,
                    geocoded_address_id,
                    is_multi_property,
                    original_address,
                    pattern_type,
                    address_position,
                    is_primary
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                tx_id,
                geocoded_address_id,
                parsed['is_multi_property'],
                parsed['original_address'],
                parsed['pattern_type'],
                addr_data['position'],
                addr_data['position'] == 1  # First address is primary
            ))

            conn.commit()

            # Rate limiting
            time.sleep(0.5)

        print()

    print("=" * 100)
    print("PROCESSING COMPLETE")
    print("=" * 100)
    print(f"Transactions processed: {total}")
    print(f"Multi-property transactions: {multi_property_count} ({multi_property_count*100/total:.1f}%)")
    print(f"Total addresses geocoded: {total_addresses_geocoded}")
    print(f"Successful geocodes: {success_count} ({success_count*100/total_addresses_geocoded:.1f}%)")
    print(f"Failed geocodes: {failure_count} ({failure_count*100/total_addresses_geocoded:.1f}%)")

    cur.close()
    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Geocode with multi-property parsing')
    parser.add_argument('--limit', type=int, default=100, help='Number of transactions to process')
    args = parser.parse_args()

    geocode_with_multi_property(args.limit)
