"""
Fix low confidence addresses using Text Search API fallback
Re-geocodes addresses that failed with standard geocoding
"""
import os
import sys
import time
import psycopg2
from psycopg2.extras import Json

sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')
from common.enhanced_geocoder import EnhancedGeocoder


def fix_low_confidence_addresses():
    """Re-geocode low confidence addresses with Text Search fallback"""

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()
    geocoder = EnhancedGeocoder()

    if not geocoder.available():
        print("❌ Google API key not found!")
        return

    print("Fixing Low Confidence Addresses")
    print("=" * 100)

    # Find addresses with no postal code (low confidence)
    cur.execute("""
        SELECT
            g.id,
            g.input_address,
            p.expanded_full_address,
            p.original_address_raw,
            g.google_postal_code,
            g.google_formatted_address
        FROM google_geocoded_addresses g
        JOIN transaction_address_expansion_parse p ON p.id = g.source_id
        WHERE g.source_table = 'transaction_address_expansion_parse'
            AND g.geocode_success = TRUE
            AND g.google_postal_code IS NULL
        ORDER BY p.original_address_raw
    """)

    addresses = cur.fetchall()
    total = len(addresses)

    print(f"Found {total} low confidence addresses to fix\n")

    fixed_count = 0
    still_failed = 0

    for i, (geocode_id, input_addr, expanded_addr, original_addr, postal, formatted) in enumerate(addresses, 1):
        print(f"[{i}/{total}] {expanded_addr}")
        print(f"  Current: {formatted or 'NO FORMATTED ADDRESS'}")
        print(f"  Postal: {postal or 'NO POSTAL'}")

        # Use enhanced geocoder with fallback
        result = geocoder.geocode_with_fallback(input_addr)

        if result.get('components', {}).get('postal_code'):
            # Success! Update the record
            components = result['components']
            location = result['location']

            cur.execute("""
                UPDATE google_geocoded_addresses
                SET
                    google_formatted_address = %s,
                    google_street_number = %s,
                    google_street = %s,
                    google_city = %s,
                    google_province = %s,
                    google_postal_code = %s,
                    google_latitude = %s,
                    google_longitude = %s,
                    google_place_id = %s,
                    google_confidence = %s,
                    google_raw_response = %s,
                    geocode_method = %s,
                    needs_manual_review = FALSE
                WHERE id = %s
            """, (
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
                Json(result.get('raw')),
                result.get('method'),
                geocode_id
            ))

            fixed_count += 1
            print(f"  ✓ FIXED ({result.get('method')}): {result.get('formatted_address')}")
            print(f"    Postal: {components.get('postal_code')}")
        else:
            # Still failed - flag for manual review
            cur.execute("""
                UPDATE google_geocoded_addresses
                SET
                    needs_manual_review = TRUE,
                    geocode_method = %s
                WHERE id = %s
            """, (
                result.get('method', 'geocoding'),
                geocode_id
            ))

            still_failed += 1
            print(f"  ✗ STILL FAILED - flagged for manual review")

        conn.commit()
        time.sleep(0.3)  # Rate limiting
        print()

    print("=" * 100)
    print("RESULTS")
    print("=" * 100)
    print(f"Total low confidence addresses: {total}")
    print(f"Fixed with Text Search: {fixed_count} ({fixed_count*100/total:.1f}%)")
    print(f"Still need manual review: {still_failed} ({still_failed*100/total:.1f}%)")

    if still_failed > 0:
        print(f"\n⚠️ {still_failed} addresses flagged with needs_manual_review = TRUE")
        print(f"   These can be fixed manually in the app later")

    cur.close()
    conn.close()


if __name__ == "__main__":
    fix_low_confidence_addresses()
