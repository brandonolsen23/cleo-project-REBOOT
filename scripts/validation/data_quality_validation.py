"""
Data Quality Validation Report
Validates geocoded data for anomalies, patterns, and quality issues
"""
import os
import sys
import psycopg2
from collections import defaultdict

sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')


def validate_data_quality():
    """Run comprehensive data quality checks"""

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    print("DATA QUALITY VALIDATION REPORT")
    print("=" * 100)
    print()

    # TEST 1: Coordinate clustering (detect duplicate coordinates)
    print("TEST 1: COORDINATE CLUSTERING")
    print("-" * 100)
    cur.execute("""
        SELECT
            google_latitude,
            google_longitude,
            COUNT(*) as count,
            STRING_AGG(DISTINCT p.expanded_full_address, ' | ') as addresses
        FROM google_geocoded_addresses g
        JOIN transaction_address_expansion_parse p ON p.id = g.source_id
        WHERE g.source_table = 'transaction_address_expansion_parse'
            AND g.google_latitude IS NOT NULL
        GROUP BY google_latitude, google_longitude
        HAVING COUNT(*) > 5
        ORDER BY count DESC
        LIMIT 10
    """)

    clusters = cur.fetchall()
    if clusters:
        print(f"⚠️  Found {len(clusters)} coordinate clusters with >5 addresses")
        print("   (This may indicate Google returning city centers)")
        for lat, lng, count, addrs in clusters[:3]:
            print(f"   - {lat}, {lng}: {count} addresses")
            print(f"     Sample: {addrs[:100]}...")
    else:
        print("✓ No suspicious coordinate clustering detected")
    print()

    # TEST 2: City consistency check
    print("TEST 2: CITY CONSISTENCY")
    print("-" * 100)
    cur.execute("""
        SELECT
            p.original_city_raw,
            g.google_city,
            COUNT(*) as count
        FROM google_geocoded_addresses g
        JOIN transaction_address_expansion_parse p ON p.id = g.source_id
        WHERE g.source_table = 'transaction_address_expansion_parse'
            AND p.original_city_raw IS NOT NULL
            AND p.original_city_raw != g.google_city
            AND p.original_city_raw NOT LIKE '%York%'  -- Known amalgamation
            AND p.original_city_raw NOT LIKE '%Scarborough%'
            AND p.original_city_raw NOT LIKE '%Etobicoke%'
        GROUP BY p.original_city_raw, g.google_city
        ORDER BY count DESC
        LIMIT 10
    """)

    city_mismatches = cur.fetchall()
    total_mismatches = sum(row[2] for row in city_mismatches)
    if city_mismatches:
        print(f"⚠️  Found {total_mismatches} city mismatches (excluding Toronto amalgamation)")
        print("   Top mismatches:")
        for orig, google, count in city_mismatches[:5]:
            print(f"   - {orig} → {google}: {count} addresses")
    else:
        print("✓ No unexpected city mismatches")
    print()

    # TEST 3: Multi-property range validation
    print("TEST 3: MULTI-PROPERTY RANGE VALIDATION")
    print("-" * 100)
    cur.execute("""
        SELECT
            p1.original_address_raw,
            p1.expanded_full_address as addr1,
            p2.expanded_full_address as addr2,
            g1.google_latitude as lat1,
            g1.google_longitude as lng1,
            g2.google_latitude as lat2,
            g2.google_longitude as lng2
        FROM transaction_address_expansion_parse p1
        JOIN transaction_address_expansion_parse p2
            ON p1.original_address_raw = p2.original_address_raw
            AND p1.id < p2.id
        JOIN google_geocoded_addresses g1 ON g1.source_id = p1.id
        JOIN google_geocoded_addresses g2 ON g2.source_id = p2.id
        WHERE p1.is_multi_property = TRUE
            AND p1.pattern_type = 'range_dash'
            AND g1.google_latitude = g2.google_latitude
            AND g1.google_longitude = g2.google_longitude
            AND g1.source_table = 'transaction_address_expansion_parse'
            AND g2.source_table = 'transaction_address_expansion_parse'
        LIMIT 10
    """)

    duplicate_ranges = cur.fetchall()
    if duplicate_ranges:
        print(f"⚠️  Found {len(duplicate_ranges)} range addresses with identical coordinates")
        print("   (Google couldn't distinguish between start/end of range)")
        for orig, addr1, addr2, lat1, lng1, lat2, lng2 in duplicate_ranges[:3]:
            print(f"   - {orig}")
            print(f"     {addr1} → {lat1}, {lng1}")
            print(f"     {addr2} → {lat2}, {lng2}")
    else:
        print("✓ All multi-property ranges have distinct coordinates")
    print()

    # TEST 4: Highway address quality
    print("TEST 4: HIGHWAY ADDRESS QUALITY")
    print("-" * 100)
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN google_postal_code IS NULL THEN 1 END) as no_postal,
            COUNT(CASE WHEN google_formatted_address LIKE '%Canada%'
                       AND google_formatted_address NOT LIKE '%,%,%' THEN 1 END) as city_only
        FROM google_geocoded_addresses g
        JOIN transaction_address_expansion_parse p ON p.id = g.source_id
        WHERE g.source_table = 'transaction_address_expansion_parse'
            AND (p.expanded_full_address LIKE '%HWY%'
                 OR p.expanded_full_address LIKE '%HIGHWAY%')
    """)

    hwy_total, hwy_no_postal, hwy_city_only = cur.fetchone()
    if hwy_total > 0:
        success_rate = ((hwy_total - hwy_no_postal) * 100 / hwy_total)
        print(f"Highway addresses: {hwy_total}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Missing postal: {hwy_no_postal} ({hwy_no_postal*100/hwy_total:.1f}%)")
        print(f"City-level only: {hwy_city_only} ({hwy_city_only*100/hwy_total:.1f}%)")
        if success_rate < 50:
            print("⚠️  Highway addresses have low success rate")
        else:
            print("✓ Highway addresses performing reasonably")
    else:
        print("✓ No highway addresses in sample")
    print()

    # TEST 5: Postal code format validation
    print("TEST 5: POSTAL CODE FORMAT VALIDATION")
    print("-" * 100)
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN google_postal_code ~ '^[A-Z][0-9][A-Z] [0-9][A-Z][0-9]$'
                       THEN 1 END) as valid_format,
            COUNT(CASE WHEN google_postal_code IS NOT NULL
                       AND google_postal_code !~ '^[A-Z][0-9][A-Z] [0-9][A-Z][0-9]$'
                       THEN 1 END) as invalid_format
        FROM google_geocoded_addresses
        WHERE source_table = 'transaction_address_expansion_parse'
            AND google_postal_code IS NOT NULL
    """)

    total, valid_format, invalid_format = cur.fetchone()
    if total > 0:
        print(f"Total with postal codes: {total}")
        print(f"Valid format (A0A 0A0): {valid_format} ({valid_format*100/total:.1f}%)")
        print(f"Invalid format: {invalid_format} ({invalid_format*100/total:.1f}%)")
        if invalid_format > 0:
            print("⚠️  Some postal codes have invalid format")
        else:
            print("✓ All postal codes have valid format")
    print()

    # TEST 6: Distance anomaly detection (addresses on same street)
    print("TEST 6: DISTANCE ANOMALY DETECTION")
    print("-" * 100)
    cur.execute("""
        WITH street_groups AS (
            SELECT
                REGEXP_REPLACE(p.expanded_full_address, '^[0-9]+ ', '') as street_name,
                AVG(g.google_latitude) as avg_lat,
                AVG(g.google_longitude) as avg_lng,
                COUNT(*) as count
            FROM google_geocoded_addresses g
            JOIN transaction_address_expansion_parse p ON p.id = g.source_id
            WHERE g.source_table = 'transaction_address_expansion_parse'
                AND g.google_latitude IS NOT NULL
            GROUP BY street_name
            HAVING COUNT(*) >= 3
        )
        SELECT
            sg.street_name,
            sg.count,
            p.expanded_full_address,
            g.google_latitude,
            g.google_longitude,
            SQRT(
                POW(69.0 * (g.google_latitude - sg.avg_lat), 2) +
                POW(69.0 * (g.google_longitude - sg.avg_lng) * COS(sg.avg_lat / 57.3), 2)
            ) as distance_miles
        FROM street_groups sg
        JOIN transaction_address_expansion_parse p
            ON REGEXP_REPLACE(p.expanded_full_address, '^[0-9]+ ', '') = sg.street_name
        JOIN google_geocoded_addresses g ON g.source_id = p.id
        WHERE g.source_table = 'transaction_address_expansion_parse'
            AND SQRT(
                POW(69.0 * (g.google_latitude - sg.avg_lat), 2) +
                POW(69.0 * (g.google_longitude - sg.avg_lng) * COS(sg.avg_lat / 57.3), 2)
            ) > 10  -- More than 10 miles from street average
        LIMIT 5
    """)

    anomalies = cur.fetchall()
    if anomalies:
        print(f"⚠️  Found {len(anomalies)} addresses far from their street average")
        print("   (May indicate geocoding errors or street name duplicates)")
        for street, count, addr, lat, lng, dist in anomalies[:3]:
            print(f"   - {addr}")
            print(f"     {dist:.1f} miles from {count} other addresses on {street}")
    else:
        print("✓ No distance anomalies detected")
    print()

    # TEST 7: Transaction linkage integrity
    print("TEST 7: TRANSACTION LINKAGE INTEGRITY")
    print("-" * 100)
    cur.execute("""
        SELECT
            COUNT(DISTINCT l.transaction_id) as transactions_with_links,
            COUNT(*) as total_links,
            COUNT(CASE WHEN l.is_primary THEN 1 END) as primary_links,
            COUNT(CASE WHEN l.is_multi_property THEN 1 END) as multi_property_links
        FROM transaction_address_links l
    """)

    tx_with_links, total_links, primary_links, multi_links = cur.fetchone()

    cur.execute("SELECT COUNT(*) FROM transaction_address_expansion_parse")
    total_parsed = cur.fetchone()[0]

    print(f"Transactions with links: {tx_with_links}")
    print(f"Total address links: {total_links}")
    print(f"Primary addresses: {primary_links}")
    print(f"Multi-property links: {multi_links} ({multi_links*100/total_links:.1f}%)")

    if total_links != total_parsed:
        print(f"⚠️  Link count mismatch: {total_links} links vs {total_parsed} parsed addresses")
    else:
        print("✓ All parsed addresses have transaction links")
    print()

    # SUMMARY
    print()
    print("=" * 100)
    print("VALIDATION SUMMARY")
    print("=" * 100)

    issues = []
    if clusters:
        issues.append(f"Coordinate clustering ({len(clusters)} clusters)")
    if total_mismatches > 10:
        issues.append(f"City mismatches ({total_mismatches} addresses)")
    if duplicate_ranges:
        issues.append(f"Range address duplicates ({len(duplicate_ranges)} ranges)")
    if hwy_total > 0 and (hwy_no_postal * 100 / hwy_total) > 20:
        issues.append(f"Highway address quality ({hwy_no_postal}/{hwy_total} failed)")
    if invalid_format > 0:
        issues.append(f"Invalid postal formats ({invalid_format} addresses)")
    if anomalies:
        issues.append(f"Distance anomalies ({len(anomalies)} addresses)")
    if total_links != total_parsed:
        issues.append("Transaction linkage mismatch")

    if issues:
        print(f"⚠️  Found {len(issues)} potential issues:")
        for issue in issues:
            print(f"   - {issue}")
        print()
        print("Recommendation: Review flagged addresses before full rollout")
    else:
        print("✅ All validation tests passed!")
        print("   Data quality looks good for full rollout")

    cur.close()
    conn.close()


if __name__ == "__main__":
    validate_data_quality()
