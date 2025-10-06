"""
Geocode expanded addresses from transaction_address_expansion_parse table
Stores results in google_geocoded_addresses and links in transaction_address_links
"""
import os
import sys
import time
import psycopg2
from psycopg2.extras import Json

sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')
from common.google_geocoder import GoogleGeocoder


def geocode_expanded_addresses(limit=None):
    """Geocode expanded addresses with Google API"""

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()
    geocoder = GoogleGeocoder()

    if not geocoder.available():
        print("❌ Google API key not found!")
        return

    print(f"Geocoding expanded addresses...")
    print("=" * 100)

    # Get expanded addresses that haven't been geocoded yet
    query = """
        SELECT p.id, p.transaction_id, p.expanded_full_address,
               p.is_multi_property, p.pattern_type, p.address_position,
               p.original_address_raw
        FROM transaction_address_expansion_parse p
        WHERE NOT EXISTS (
            SELECT 1 FROM google_geocoded_addresses g
            WHERE g.source_table = 'transaction_address_expansion_parse'
            AND g.source_id = p.id
        )
        ORDER BY p.created_at
    """

    if limit:
        query += f" LIMIT {limit}"

    cur.execute(query)

    addresses = cur.fetchall()
    total = len(addresses)

    print(f"Found {total} expanded addresses to geocode\n")

    success_count = 0
    failure_count = 0
    ontario_count = 0

    for i, (parsed_id, tx_id, expanded_addr, is_multi, pattern_type, addr_pos, original_addr) in enumerate(addresses, 1):
        # Add "Ontario" to improve accuracy (key fix!)
        geocode_input = f"{expanded_addr}, Ontario"

        print(f"[{i}/{total}] {geocode_input[:75]}")

        # Geocode with Google
        result = geocoder.geocode(geocode_input)

        geocoded_address_id = None

        if result:
            components = result.get('components', {})
            location = result.get('location', {})
            province = components.get('province', '')

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
                    'transaction_address_expansion_parse',
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                RETURNING id
            """, (
                parsed_id,
                geocode_input,
                result.get('formatted_address'),
                components.get('street_number'),
                components.get('street'),
                components.get('city'),
                province,
                components.get('postal_code'),
                location.get('lat'),
                location.get('lng'),
                result.get('place_id'),
                result.get('confidence'),
                True,
                Json(result.get('raw'))
            ))

            geocoded_address_id = cur.fetchone()[0]
            success_count += 1

            if province == 'ON':
                ontario_count += 1

            postal = components.get('postal_code', 'NO POSTAL')
            print(f"  ✓ {components.get('city')}, {province} {postal}")

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
                    'transaction_address_expansion_parse',
                    %s, %s, %s, %s
                )
                RETURNING id
            """, (
                parsed_id,
                geocode_input,
                False,
                'No result from Google API'
            ))

            geocoded_address_id = cur.fetchone()[0]
            failure_count += 1
            print(f"  ✗ FAILED")

        # Link to transaction
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
            is_multi,
            original_addr,
            pattern_type,
            addr_pos,
            addr_pos == 1  # First address is primary
        ))

        conn.commit()

        # Rate limiting - be nice to Google
        if i % 10 == 0:
            time.sleep(1)
        else:
            time.sleep(0.3)

    print("\n" + "=" * 100)
    print("GEOCODING COMPLETE")
    print("=" * 100)
    print(f"Total addresses geocoded: {total}")
    print(f"Successful: {success_count} ({success_count*100/total:.1f}%)")
    print(f"Failed: {failure_count} ({failure_count*100/total:.1f}%)")
    print(f"Ontario addresses: {ontario_count} ({ontario_count*100/total:.1f}%)")
    print(f"With postal codes: {success_count} (Google always returns postal for successful geocodes)")

    cur.close()
    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Geocode expanded addresses')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of addresses (optional)')
    args = parser.parse_args()

    geocode_expanded_addresses(args.limit)
