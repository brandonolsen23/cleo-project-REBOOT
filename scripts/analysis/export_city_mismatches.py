"""
Export city mismatch data for manual review
"""
import os
import sys
import psycopg2
import csv

sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')

def export_city_mismatches():
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    cur.execute("""
        SELECT
            p.original_address_raw,
            p.expanded_full_address,
            p.original_city_raw as original_city,
            g.google_city as geocoded_city,
            g.google_formatted_address,
            g.google_postal_code
        FROM google_geocoded_addresses g
        JOIN transaction_address_expansion_parse p ON p.id = g.source_id
        WHERE g.source_table = 'transaction_address_expansion_parse'
            AND p.original_city_raw IS NOT NULL
            AND p.original_city_raw != g.google_city
            AND (g.is_amalgamation_match = FALSE OR g.is_amalgamation_match IS NULL)
        ORDER BY p.original_city_raw, g.google_city
    """)

    rows = cur.fetchall()

    # Print to console
    print(f"CITY MISMATCH REVIEW - {len(rows)} addresses")
    print("=" * 150)
    print(f"{'Original City':<20} {'Geocoded City':<20} {'Original Address':<40} {'Geocoded Address':<50}")
    print("-" * 150)

    for row in rows:
        orig_addr, expanded, orig_city, geo_city, formatted, postal = row
        print(f"{orig_city:<20} {geo_city:<20} {orig_addr:<40} {formatted[:48] if formatted else 'N/A':<50}")

    # Also save to CSV
    with open('/tmp/unresolved_city_mismatches.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Original Address', 'Expanded Address', 'Original City', 'Geocoded City', 'Google Formatted Address', 'Postal Code'])
        writer.writerows(rows)

    print()
    print(f"Data also saved to: /tmp/unresolved_city_mismatches.csv")

    cur.close()
    conn.close()

if __name__ == "__main__":
    export_city_mismatches()
