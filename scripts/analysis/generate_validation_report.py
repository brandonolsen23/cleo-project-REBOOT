#!/usr/bin/env python3
"""
Generate CSV Validation Report

Creates a CSV file comparing raw addresses vs NAR-validated addresses
for manual quality review.

Columns:
1. Raw Data: address_line1, city, postal_code
2. NAR Validated: validated_city, validated_postal, confidence_score
3. Status: nar_found, match_type

Usage:
    python3 scripts/analysis/generate_validation_report.py [--limit N]

Date: 2025-10-03
"""

import os
import sys
import csv
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.db import connect_with_retries


def generate_validation_report(output_file: str = None, limit: int = None):
    """
    Generate CSV report of completed validations.

    Args:
        output_file: Output CSV path (default: validation_report_YYYYMMDD_HHMMSS.csv)
        limit: Limit number of records (default: all completed)
    """
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"validation_report_{timestamp}.csv"

    print("=" * 70)
    print("VALIDATION REPORT GENERATOR")
    print("=" * 70)
    print()

    conn = connect_with_retries()
    cursor = conn.cursor()

    try:
        # Fetch completed validations with property data
        limit_clause = f"LIMIT {limit}" if limit else ""

        cursor.execute(f"""
            SELECT
                -- Property data
                p.id,
                p.address_line1,

                -- BEFORE validation
                q.city_before,
                q.postal_code_before,

                -- NAR RESULT (what NAR returned)
                q.city_after as nar_city_result,
                q.postal_code_after as nar_postal_result,
                q.confidence_score,
                q.nar_found,

                -- AFTER validation (actual current values in DB)
                p.city as city_final,
                p.postal_code as postal_final,
                p.latitude,
                p.longitude,
                q.geocoding_updated,

                q.completed_at
            FROM nar_validation_queue q
            JOIN properties p ON q.property_id = p.id
            WHERE q.status = 'completed'
            ORDER BY q.completed_at DESC
            {limit_clause}
        """)

        rows = cursor.fetchall()

        if not rows:
            print("❌ No completed validations found")
            print()
            return

        print(f"📊 Found {len(rows)} completed validations")
        print()

        # Write CSV
        print(f"📝 Writing CSV to: {output_file}")

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Property ID',
                'Address Line 1',
                '--- BEFORE VALIDATION ---',
                'City (Before)',
                'Postal Code (Before)',
                '--- NAR RESULT ---',
                'City from NAR',
                'Postal from NAR',
                'Confidence Score',
                'Found in NAR',
                '--- AFTER VALIDATION (FINAL) ---',
                'City (Final in DB)',
                'Postal Code (Final in DB)',
                'Latitude',
                'Longitude',
                'Geocoding Updated',
                'Completed At'
            ])

            # Data rows
            for row in rows:
                (prop_id, address,
                 city_before, postal_before,
                 nar_city, nar_postal, confidence, nar_found,
                 city_final, postal_final,
                 lat, lon, geo_updated,
                 completed_at) = row

                writer.writerow([
                    str(prop_id),
                    address or '',
                    '',  # Separator
                    city_before or '',
                    postal_before or '',
                    '',  # Separator
                    nar_city or '',
                    nar_postal or '',
                    confidence if confidence is not None else '',
                    'YES' if nar_found else 'NO',
                    '',  # Separator
                    city_final or '',
                    postal_final or '',
                    f'{lat:.6f}' if lat else '',
                    f'{lon:.6f}' if lon else '',
                    'YES' if geo_updated else 'NO',
                    str(completed_at) if completed_at else ''
                ])

        print(f"   ✅ Wrote {len(rows)} records")
        print()

        # Summary statistics
        print("📈 SUMMARY STATISTICS")
        print("-" * 70)

        # New column positions: (prop_id, address, city_before, postal_before, nar_city, nar_postal, confidence, nar_found, city_final, postal_final, lat, lon, geo_updated, completed_at)
        found_count = sum(1 for r in rows if r[7])  # nar_found
        high_conf = sum(1 for r in rows if r[6] and r[6] >= 90)  # confidence >= 90
        city_updated = sum(1 for r in rows if r[2] != r[8])  # city_before != city_final
        postal_updated = sum(1 for r in rows if r[3] != r[9] and r[9])  # postal updated
        geo_updated = sum(1 for r in rows if r[12])  # geocoding_updated

        print(f"  Total validations:     {len(rows):>6,}")
        print(f"  Found in NAR:          {found_count:>6,} ({found_count/len(rows)*100:5.1f}%)")
        print(f"  High confidence (≥90): {high_conf:>6,} ({high_conf/len(rows)*100:5.1f}%)")
        print(f"  City updated:          {city_updated:>6,} ({city_updated/len(rows)*100:5.1f}%)")
        print(f"  Postal code updated:   {postal_updated:>6,} ({postal_updated/len(rows)*100:5.1f}%)")
        print(f"  Geocoding updated:     {geo_updated:>6,} ({geo_updated/len(rows)*100:5.1f}%)")
        print()

        # Confidence distribution
        print("📊 CONFIDENCE DISTRIBUTION")
        print("-" * 70)

        conf_100 = sum(1 for r in rows if r[6] == 100)
        conf_90 = sum(1 for r in rows if r[6] == 90)
        conf_70 = sum(1 for r in rows if r[6] == 70)
        conf_0 = sum(1 for r in rows if r[6] == 0)

        print(f"  100 (Postal + Address): {conf_100:>6,} ({conf_100/len(rows)*100:5.1f}%)")
        print(f"   90 (City + Address):   {conf_90:>6,} ({conf_90/len(rows)*100:5.1f}%)")
        print(f"   70 (Fuzzy):            {conf_70:>6,} ({conf_70/len(rows)*100:5.1f}%)")
        print(f"    0 (Not found):        {conf_0:>6,} ({conf_0/len(rows)*100:5.1f}%)")
        print()

    finally:
        cursor.close()
        conn.close()

    print("=" * 70)
    print("REPORT COMPLETE")
    print("=" * 70)
    print()
    print(f"✅ CSV report saved to: {output_file}")
    print()
    print("📖 Open in Excel/Numbers for manual review")
    print("   Compare 'RAW DATA' vs 'NAR VALIDATION' columns")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate NAR validation CSV report")
    parser.add_argument('--limit', type=int, help="Limit number of records")
    parser.add_argument('--output', type=str, help="Output CSV file path")

    args = parser.parse_args()

    generate_validation_report(output_file=args.output, limit=args.limit)
