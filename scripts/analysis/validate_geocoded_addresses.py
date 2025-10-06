"""
Validate geocoded addresses without requiring Places API
Uses postal codes, duplicate coordinates, and formatted address analysis
"""
import os
import sys
import psycopg2

sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')


def validate_geocoded_addresses():
    """Validate all geocoded addresses and assign confidence scores"""

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    print("Validating Geocoded Addresses")
    print("=" * 100)

    # Get all geocoded addresses from expansion table
    cur.execute("""
        SELECT
            p.id,
            p.expanded_full_address,
            p.original_address_raw,
            p.is_multi_property,
            p.pattern_type,
            p.address_position,
            g.google_formatted_address,
            g.google_postal_code,
            g.google_latitude,
            g.google_longitude,
            g.google_confidence
        FROM transaction_address_expansion_parse p
        JOIN google_geocoded_addresses g ON g.source_id = p.id
        WHERE g.source_table = 'transaction_address_expansion_parse'
        ORDER BY p.original_address_raw, p.address_position
    """)

    addresses = cur.fetchall()
    total = len(addresses)

    print(f"Found {total} geocoded addresses to validate\n")

    # Group by original address
    from collections import defaultdict
    grouped = defaultdict(list)
    for addr_data in addresses:
        original = addr_data[2]  # original_address_raw
        grouped[original].append(addr_data)

    high_conf = []
    medium_conf = []
    low_conf = []
    failed = []

    for original_addr, addr_list in grouped.items():
        is_multi = addr_list[0][3]
        pattern = addr_list[0][4]

        # Check for range addresses with duplicate coordinates
        if is_multi and pattern == 'range_dash' and len(addr_list) == 2:
            start_data = addr_list[0]
            end_data = addr_list[1]

            start_lat = start_data[8]
            start_lng = start_data[9]
            end_lat = end_data[8]
            end_lng = end_data[9]

            # Duplicate coordinates = Google guessing
            if start_lat == end_lat and start_lng == end_lng:
                print(f"⚠️ DUPLICATE COORDS: {original_addr}")
                print(f"   Both addresses geocoded to same point: {start_lat}, {start_lng}")
                print(f"   Google is guessing - LOW CONFIDENCE\n")
                low_conf.extend(addr_list)
                continue

        # Validate each address individually
        for addr_data in addr_list:
            parsed_id = addr_data[0]
            expanded = addr_data[1]
            formatted = addr_data[6]
            postal = addr_data[7]
            google_conf = addr_data[10]

            # Confidence scoring
            if postal:
                # Has postal code
                if ',' in formatted and any(char.isdigit() for char in formatted.split(',')[0]):
                    # Formatted address has street number
                    confidence = 'HIGH'
                    high_conf.append(addr_data)
                else:
                    # Has postal but formatted address is vague
                    confidence = 'MEDIUM'
                    medium_conf.append(addr_data)
            else:
                # No postal code
                if formatted and ',' in formatted and any(char.isdigit() for char in formatted.split(',')[0]):
                    # No postal but has detailed formatted address
                    confidence = 'MEDIUM'
                    medium_conf.append(addr_data)
                else:
                    # No postal and vague formatted address
                    confidence = 'LOW'
                    low_conf.append(addr_data)

    # Summary
    print("\n" + "=" * 100)
    print("VALIDATION SUMMARY")
    print("=" * 100)

    print(f"\n✓ HIGH CONFIDENCE: {len(high_conf)} addresses ({len(high_conf)*100/total:.1f}%)")
    print(f"  - Has postal code + detailed formatted address")

    print(f"\n~ MEDIUM CONFIDENCE: {len(medium_conf)} addresses ({len(medium_conf)*100/total:.1f}%)")
    print(f"  - Has postal code OR detailed formatted address")

    print(f"\n⚠️ LOW CONFIDENCE: {len(low_conf)} addresses ({len(low_conf)*100/total:.1f}%)")
    print(f"  - No postal code + vague formatted address")
    print(f"  - OR duplicate coordinates (Google guessing)")

    if low_conf:
        print(f"\n\nLOW CONFIDENCE ADDRESSES REQUIRING REVIEW:")
        print("-" * 100)
        for addr_data in low_conf:
            expanded = addr_data[1]
            formatted = addr_data[6]
            postal = addr_data[7] or 'NO POSTAL'
            print(f"  {expanded}")
            print(f"    → {formatted}")
            print(f"    → {postal}")
            print()

    # Export low confidence addresses for manual review
    print("\n" + "=" * 100)
    print("EXPORT FOR MANUAL REVIEW")
    print("=" * 100)

    if low_conf:
        print(f"\n{len(low_conf)} addresses need manual verification:")
        for addr_data in low_conf:
            print(f"  - {addr_data[1]}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    validate_geocoded_addresses()
