"""
Address Quality Review
Runs AFTER geocoding to flag addresses needing manual review
Updates quality_reviewed = TRUE and needs_manual_review flag
"""
import os
import sys
import psycopg2
from collections import defaultdict

sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')


def review_geocoded_addresses():
    """Review geocoded addresses and flag low quality ones"""

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    print("Address Quality Review")
    print("=" * 100)

    # Get all geocoded addresses that haven't been reviewed
    cur.execute("""
        SELECT
            g.id,
            p.id as parse_id,
            p.expanded_full_address,
            p.original_address_raw,
            p.is_multi_property,
            p.pattern_type,
            p.address_position,
            g.google_formatted_address,
            g.google_postal_code,
            g.google_latitude,
            g.google_longitude
        FROM google_geocoded_addresses g
        JOIN transaction_address_expansion_parse p ON p.id = g.source_id
        WHERE g.source_table = 'transaction_address_expansion_parse'
            AND g.geocode_success = TRUE
            AND g.quality_reviewed = FALSE
        ORDER BY p.original_address_raw, p.address_position
    """)

    addresses = cur.fetchall()
    total = len(addresses)

    print(f"Reviewing {total} geocoded addresses\n")

    # Group by original address for range validation
    grouped = defaultdict(list)
    for addr_data in addresses:
        original = addr_data[3]  # original_address_raw
        grouped[original].append(addr_data)

    reviewed_count = 0
    flagged_count = 0
    flagged_addresses = []

    for original_addr, addr_list in grouped.items():
        is_multi = addr_list[0][4]
        pattern = addr_list[0][5]

        # Check for range addresses with duplicate coordinates
        if is_multi and pattern == 'range_dash' and len(addr_list) == 2:
            start_data = addr_list[0]
            end_data = addr_list[1]

            start_lat = start_data[9]
            start_lng = start_data[10]
            end_lat = end_data[9]
            end_lng = end_data[10]

            # Duplicate coordinates = Google guessing
            if start_lat == end_lat and start_lng == end_lng:
                print(f"⚠️ DUPLICATE COORDS: {original_addr}")
                print(f"   Both addresses at: {start_lat}, {start_lng}")

                # Flag both addresses
                for addr_data in addr_list:
                    geocode_id = addr_data[0]
                    expanded = addr_data[2]

                    cur.execute("""
                        UPDATE google_geocoded_addresses
                        SET quality_reviewed = TRUE,
                            needs_manual_review = TRUE
                        WHERE id = %s
                    """, (geocode_id,))

                    flagged_count += 1
                    flagged_addresses.append(expanded)

                reviewed_count += 2
                print(f"   → Flagged for manual review\n")
                continue

        # Review each address individually
        for addr_data in addr_list:
            geocode_id = addr_data[0]
            expanded = addr_data[2]
            formatted = addr_data[7]
            postal = addr_data[8]

            # Quality checks
            needs_review = False
            reason = None

            if not postal:
                needs_review = True
                reason = "No postal code"
            elif formatted and formatted.count(',') <= 2:
                # Check if formatted address is just "City, Province, Country"
                first_part = formatted.split(',')[0].strip()
                if not any(char.isdigit() for char in first_part):
                    needs_review = True
                    reason = "Vague formatted address (city-level only)"

            # Update database
            cur.execute("""
                UPDATE google_geocoded_addresses
                SET quality_reviewed = TRUE,
                    needs_manual_review = %s
                WHERE id = %s
            """, (needs_review, geocode_id))

            reviewed_count += 1

            if needs_review:
                flagged_count += 1
                flagged_addresses.append(expanded)
                print(f"⚠️ {expanded}")
                print(f"   {reason}")
                print(f"   Formatted: {formatted or 'NONE'}")
                print(f"   → Flagged for manual review\n")

    conn.commit()

    # Summary
    print("=" * 100)
    print("QUALITY REVIEW COMPLETE")
    print("=" * 100)
    print(f"Addresses reviewed: {reviewed_count}")
    print(f"Passed quality check: {reviewed_count - flagged_count} ({(reviewed_count-flagged_count)*100/reviewed_count:.1f}%)")
    print(f"Flagged for manual review: {flagged_count} ({flagged_count*100/reviewed_count:.1f}%)")

    if flagged_addresses:
        print(f"\n\nADDRESSES FLAGGED FOR MANUAL REVIEW:")
        print("-" * 100)
        for addr in flagged_addresses:
            print(f"  - {addr}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    review_geocoded_addresses()
