"""
Resolve City Amalgamations in Geocoded Addresses

Identifies and flags geocoding results where the original city name is a former
municipality that has been amalgamated into a larger city (e.g., Nepean → Ottawa).

Usage:
    python3 scripts/fixes/resolve_city_amalgamations.py           # Dry run (preview)
    python3 scripts/fixes/resolve_city_amalgamations.py --apply   # Apply changes
"""
import os
import sys
import psycopg2
import argparse

sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')


# City Amalgamations - Source of Truth
# Amalgamated city → List of former municipalities
CITY_AMALGAMATIONS = {
    'TORONTO': [
        'ETOBICOKE', 'NORTH YORK', 'SCARBOROUGH',
        'YORK', 'EAST YORK', 'N YORK', 'E YORK',
        'N. YORK', 'E. YORK'  # With periods (will be normalized)
    ],
    'OTTAWA': [
        'NEPEAN', 'GLOUCESTER', 'KANATA', 'ORLEANS',
        'VANIER', 'CUMBERLAND', 'OSGOODE', 'RIDEAU',
        'WEST CARLETON', 'GOULBOURN', 'ROCKCLIFFE PARK'
    ],
    'HAMILTON': [
        'DUNDAS', 'FLAMBOROUGH', 'GLANBROOK', 'STONEY CREEK', 'ANCASTER'
    ],
    'GREATER SUDBURY': [
        'SUDBURY', 'VALLEY EAST', 'RAYSIDE-BALFOUR', 'ONAPING FALLS',
        'WALDEN', 'NICKEL CENTRE', 'CAPREOL', 'N. MONAGHAN'
    ],
    'CHATHAM': [
        'CHATHAM-KENT'  # Reverse - sometimes data has hyphenated form as original
    ],
    'CHATHAM-KENT': [
        'CHATHAM', 'WALLACEBURG', 'TILBURY', 'BLENHEIM', 'DRESDEN', 'MERLIN'
    ],
    'KAWARTHA LAKES': [
        'LINDSAY', 'FENELON FALLS', 'BOBCAYGEON', 'OMEMEE'
    ],
    'MISSISSIPPI MILLS': [
        'ALMONTE', 'PAKENHAM', 'CLAYTON'
    ],
    'QUINTE WEST': [
        'TRENTON', 'FRANKFORD', 'BATAWA', 'QUINTE W'  # Abbreviated form
    ],
    'FERGUS': [
        'CENTRE WELLINGTON',  # Google geocodes to Fergus, original has Centre Wellington
        'SALEM'
    ],
    'ELORA': [
        'CENTRE WELLINGTON'  # Google geocodes to Elora, original has Centre Wellington
    ],
    'CENTRE WELLINGTON': [
        'ELORA', 'FERGUS', 'SALEM'
    ],
    'ACTON': [
        'HALTON HILLS'  # Bidirectional mapping
    ],
    'GEORGETOWN': [
        'HALTON HILLS'  # Bidirectional mapping
    ],
    'HALTON HILLS': [
        'GEORGETOWN', 'ACTON'
    ],
    'BRADFORD WEST GWILLIMBURY': [
        'BRADFORD'
    ],
    'EAST GWILLIMBURY': [
        'E. GWILLIMBURY'
    ],
    'NAPANEE': [
        'GREATER NAPANEE'  # Google geocodes to Napanee, original has Greater Napanee
    ],
    'GREATER NAPANEE': [
        'NAPANEE'
    ],
    'NORTH GRENVILLE': [
        'KEMPTVILLE'
    ],
    'SAUGEEN SHORES': [
        'PORT ELGIN', 'SOUTHAMPTON'
    ],
    'SAINT MARYS': [
        'ST. MARYS', 'ST MARYS'
    ],
    'SAULT STE. MARIE': [
        'SAULT STE MARIE'
    ],
    'SAULT STE MARIE': [
        'SAULT STE. MARIE'  # Bidirectional for period variation
    ],
    'PERTH': [
        'N. PERTH', 'N PERTH', 'NORTH PERTH'
    ],
    'ANGUS': [
        'ESSA'  # Google geocodes to Angus, original has Essa
    ],
    'NOBLETON': [
        'KING'  # Google geocodes to Nobleton, original has King
    ],
    'BELLE RIVER': [
        'LAKESHORE'  # Google geocodes to Belle River, original has Lakeshore
    ],
    'INGLEWOOD': [
        'CALEDON'  # Google geocodes to Inglewood, original has Caledon
    ],
    'BOLTON': [
        'CALEDON'  # Google geocodes to Bolton, original has Caledon
    ],
    'ALTON': [
        'CALEDON'  # Google geocodes to Alton, original has Caledon
    ],
    'BOWMANVILLE': [
        'CLARINGTON', 'OSHAWA'  # Google geocodes to Bowmanville, original has Clarington
    ],
    'PORT STANLEY': [
        'CENTRAL ELGIN'  # Google geocodes to Port Stanley, original has Central Elgin
    ],
    'MARKHAM': [
        'E. YORK', 'E YORK'  # Some E. York addresses geocode to Markham (border issue)
    ],
    'EAST GWILLIMBURY': [
        'E. GWILLIMBURY', 'E GWILLIMBURY'  # Abbreviation variations
    ]
}


def build_reverse_lookup():
    """Build reverse lookup: former municipality → amalgamated city"""
    reverse = {}
    for amalgamated, former_list in CITY_AMALGAMATIONS.items():
        for former in former_list:
            reverse[former.upper().strip()] = amalgamated.upper()
    return reverse


def normalize_city(city):
    """Normalize city name for comparison"""
    if not city:
        return None
    return city.upper().strip().replace('.', '')


def check_amalgamation(original_city, google_city, reverse_lookup):
    """
    Check if original_city is a former municipality of google_city

    Returns: (is_amalgamation, amalgamated_city)
    """
    original_norm = normalize_city(original_city)
    google_norm = normalize_city(google_city)

    if not original_norm or not google_norm:
        return False, None

    # Check if original city is a former municipality
    if original_norm in reverse_lookup:
        expected_amalgamated = reverse_lookup[original_norm]
        # Check if Google returned the correct amalgamated city
        if google_norm == expected_amalgamated:
            return True, expected_amalgamated

    return False, None


def add_column_if_not_exists(conn):
    """Add is_amalgamation_match column if it doesn't exist"""
    cur = conn.cursor()

    # Check if column exists
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'google_geocoded_addresses'
        AND column_name = 'is_amalgamation_match'
    """)

    if cur.fetchone() is None:
        print("Adding is_amalgamation_match column to google_geocoded_addresses...")
        cur.execute("""
            ALTER TABLE google_geocoded_addresses
            ADD COLUMN is_amalgamation_match BOOLEAN DEFAULT FALSE
        """)
        conn.commit()
        print("✓ Column added\n")
    else:
        print("✓ Column is_amalgamation_match already exists\n")

    cur.close()


def analyze_amalgamations(dry_run=True):
    """Analyze and optionally fix city amalgamation mismatches"""

    conn = psycopg2.connect(os.environ['DATABASE_URL'])

    # Ensure column exists
    add_column_if_not_exists(conn)

    cur = conn.cursor()

    print("CITY AMALGAMATION RESOLUTION")
    print("=" * 100)
    print()

    # Build reverse lookup
    reverse_lookup = build_reverse_lookup()

    # Fetch all city mismatches
    cur.execute("""
        SELECT
            g.id,
            p.original_city_raw,
            g.google_city,
            p.expanded_full_address,
            g.google_formatted_address
        FROM google_geocoded_addresses g
        JOIN transaction_address_expansion_parse p ON p.id = g.source_id
        WHERE g.source_table = 'transaction_address_expansion_parse'
            AND p.original_city_raw IS NOT NULL
            AND g.google_city IS NOT NULL
            AND p.original_city_raw != g.google_city
            AND g.is_amalgamation_match = FALSE
        ORDER BY p.original_city_raw, g.google_city
    """)

    mismatches = cur.fetchall()
    total_mismatches = len(mismatches)

    print(f"Found {total_mismatches} city mismatches to analyze\n")

    # Analyze each mismatch
    amalgamations_found = []
    non_amalgamations = []

    for geocode_id, original_city, google_city, expanded_addr, google_formatted in mismatches:
        is_amal, amalgamated_city = check_amalgamation(original_city, google_city, reverse_lookup)

        if is_amal:
            amalgamations_found.append({
                'id': geocode_id,
                'original_city': original_city,
                'google_city': google_city,
                'amalgamated_city': amalgamated_city,
                'address': expanded_addr
            })
        else:
            non_amalgamations.append({
                'original_city': original_city,
                'google_city': google_city,
                'address': expanded_addr
            })

    # Report Results
    print("=" * 100)
    print("ANALYSIS RESULTS")
    print("=" * 100)
    print()

    print(f"✓ Confirmed Amalgamations: {len(amalgamations_found)} ({len(amalgamations_found)*100/total_mismatches:.1f}%)")
    print(f"⚠️  Non-Amalgamations: {len(non_amalgamations)} ({len(non_amalgamations)*100/total_mismatches:.1f}%)")
    print()

    # Show confirmed amalgamations by city
    if amalgamations_found:
        print("CONFIRMED AMALGAMATIONS BY CITY:")
        print("-" * 100)

        # Group by amalgamated city
        by_city = {}
        for amal in amalgamations_found:
            city = amal['amalgamated_city']
            if city not in by_city:
                by_city[city] = []
            by_city[city].append(amal)

        for city, records in sorted(by_city.items()):
            # Group by original city
            by_original = {}
            for rec in records:
                orig = rec['original_city']
                if orig not in by_original:
                    by_original[orig] = 0
                by_original[orig] += 1

            print(f"\n{city}:")
            for orig, count in sorted(by_original.items()):
                print(f"  {orig} → {city}: {count} addresses")

        print()

    # Show sample non-amalgamations
    if non_amalgamations:
        print("NON-AMALGAMATION MISMATCHES (Sample - may need manual review):")
        print("-" * 100)

        # Group by original → google city
        mismatch_counts = {}
        for rec in non_amalgamations:
            key = (rec['original_city'], rec['google_city'])
            if key not in mismatch_counts:
                mismatch_counts[key] = 0
            mismatch_counts[key] += 1

        # Show top 10
        for (orig, google), count in sorted(mismatch_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {orig} → {google}: {count} addresses")

        print()

    # Apply changes if requested
    if not dry_run and amalgamations_found:
        print("=" * 100)
        print("APPLYING CHANGES TO DATABASE")
        print("=" * 100)
        print()

        ids_to_update = [amal['id'] for amal in amalgamations_found]

        # Update in batches for safety
        for geocode_id in ids_to_update:
            cur.execute("""
                UPDATE google_geocoded_addresses
                SET is_amalgamation_match = TRUE
                WHERE id = %s
            """, (geocode_id,))

        conn.commit()

        print(f"✓ Updated {len(ids_to_update)} records with is_amalgamation_match = TRUE")
        print()

    elif dry_run and amalgamations_found:
        print("=" * 100)
        print("DRY RUN MODE - No changes made to database")
        print("=" * 100)
        print()
        print(f"Run with --apply flag to update {len(amalgamations_found)} records")
        print()

    cur.close()
    conn.close()

    return len(amalgamations_found), len(non_amalgamations)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Resolve city amalgamation mismatches')
    parser.add_argument('--apply', action='store_true',
                       help='Apply changes to database (default is dry run)')

    args = parser.parse_args()

    amalgamations, non_amalgamations = analyze_amalgamations(dry_run=not args.apply)

    print("=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"Confirmed amalgamations: {amalgamations}")
    print(f"Non-amalgamations: {non_amalgamations}")

    if not args.apply and amalgamations > 0:
        print()
        print("⚠️  Run with --apply to update the database")
