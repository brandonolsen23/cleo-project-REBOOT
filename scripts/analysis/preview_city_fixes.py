#!/usr/bin/env python3
"""
Preview City Fixes (Read-Only Analysis)
Analyzes what city fixes would be applied WITHOUT writing to the database.
Outputs results to JSON file for review.

Date: 2025-10-03
"""

import json
import os
import sys
from collections import defaultdict
from typing import Dict, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.address_parser import parse_and_validate_city
from common.db import connect_with_service_role
from common.ontario_cities import (
    is_likely_unit_or_address,
    is_valid_city,
    normalize_city,
)


def analyze_properties(cur) -> Dict:
    """Analyze properties table and preview fixes."""

    print("Fetching all properties from database...")
    cur.execute("""
        SELECT
            id,
            address_line1,
            city,
            city_backup,
            address_canonical,
            province
        FROM properties
        ORDER BY id
    """)

    properties = cur.fetchall()
    total_count = len(properties)
    print(f"✅ Loaded {total_count:,} properties\n")

    # Analysis results
    results = {
        "total_properties": total_count,
        "issues_found": 0,
        "would_fix": 0,
        "no_fix_available": 0,
        "already_valid": 0,
        "issue_types": defaultdict(int),
        "city_changes": defaultdict(list),
        "sample_fixes": [],
        "unfixable_samples": [],
    }

    print("Analyzing city data quality...\n")

    for i, prop in enumerate(properties):
        if i % 1000 == 0 and i > 0:
            print(f"  Progress: {i:,} / {total_count:,} ({i/total_count*100:.1f}%)")

        prop_id = prop['id']
        city = prop['city']
        canonical = prop['address_canonical']

        # Check if city is valid
        if is_valid_city(city):
            results["already_valid"] += 1
            continue

        # Issue found
        results["issues_found"] += 1

        # Determine issue type
        if is_likely_unit_or_address(city):
            results["issue_types"]["unit_or_address_in_city"] += 1
            issue_type = "unit_or_address"
        elif city and not is_valid_city(city):
            results["issue_types"]["invalid_city_name"] += 1
            issue_type = "invalid_city"
        elif not city:
            results["issue_types"]["null_or_empty_city"] += 1
            issue_type = "null_city"
        else:
            results["issue_types"]["other"] += 1
            issue_type = "other"

        # Try to fix
        fixed_city = parse_and_validate_city(
            address=prop['address_line1'] or "",
            city_raw=city or "",
            province=prop['province'] or "ON",
            canonical=canonical
        )

        if fixed_city:
            results["would_fix"] += 1

            # Track the change
            change_key = f"{city} → {fixed_city}"
            results["city_changes"][change_key].append(prop_id)

            # Add to sample fixes (first 20)
            if len(results["sample_fixes"]) < 20:
                results["sample_fixes"].append({
                    "property_id": prop_id,
                    "address": prop['address_line1'],
                    "current_city": city,
                    "fixed_city": fixed_city,
                    "canonical": canonical,
                    "issue_type": issue_type
                })
        else:
            results["no_fix_available"] += 1

            # Add to unfixable samples (first 20)
            if len(results["unfixable_samples"]) < 20:
                results["unfixable_samples"].append({
                    "property_id": prop_id,
                    "address": prop['address_line1'],
                    "current_city": city,
                    "canonical": canonical,
                    "issue_type": issue_type
                })

    print(f"\n✅ Analysis complete!\n")

    return results


def print_summary(results: Dict):
    """Print human-readable summary."""

    print("=" * 70)
    print("CITY FIX PREVIEW SUMMARY")
    print("=" * 70)
    print()

    print(f"📊 Overall Stats:")
    print(f"   Total properties:     {results['total_properties']:,}")
    print(f"   Already valid:        {results['already_valid']:,} ({results['already_valid']/results['total_properties']*100:.1f}%)")
    print(f"   Issues found:         {results['issues_found']:,} ({results['issues_found']/results['total_properties']*100:.1f}%)")
    print()

    print(f"🔧 Fix Analysis:")
    print(f"   Would fix:            {results['would_fix']:,} ({results['would_fix']/results['issues_found']*100:.1f}% of issues)")
    print(f"   No fix available:     {results['no_fix_available']:,} ({results['no_fix_available']/results['issues_found']*100:.1f}% of issues)")
    print()

    print(f"🏷️  Issue Types:")
    for issue_type, count in sorted(results['issue_types'].items(), key=lambda x: x[1], reverse=True):
        print(f"   {issue_type:30s} {count:,}")
    print()

    print(f"🔄 Top City Changes (showing up to 10):")
    sorted_changes = sorted(results['city_changes'].items(), key=lambda x: len(x[1]), reverse=True)
    for change, prop_ids in sorted_changes[:10]:
        print(f"   {change:50s} ({len(prop_ids):,} properties)")
    print()

    print(f"✅ Sample Fixes (showing {len(results['sample_fixes'])}):")
    for fix in results['sample_fixes'][:5]:
        print(f"   Property: {fix['property_id']}")
        print(f"   Address:  {fix['address']}")
        print(f"   Change:   '{fix['current_city']}' → '{fix['fixed_city']}'")
        print(f"   Type:     {fix['issue_type']}")
        print()

    if results['unfixable_samples']:
        print(f"❌ Unfixable Samples (showing {len(results['unfixable_samples'])}):")
        for fix in results['unfixable_samples'][:5]:
            print(f"   Property: {fix['property_id']}")
            print(f"   Address:  {fix['address']}")
            print(f"   City:     '{fix['current_city']}'")
            print(f"   Type:     {fix['issue_type']}")
            print()

    print("=" * 70)
    print()


def main():
    print("=" * 70)
    print("PREVIEW CITY FIXES (Read-Only Analysis)")
    print("=" * 70)
    print()
    print("This script will analyze city data and preview what would be fixed.")
    print("NO database changes will be made.")
    print()

    # Connect to database
    try:
        conn = connect_with_service_role()
        print("✅ Connected to database\n")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    with conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            results = analyze_properties(cur)

    conn.close()

    # Print summary
    print_summary(results)

    # Convert defaultdicts to regular dicts for JSON serialization
    results_json = {
        "total_properties": results["total_properties"],
        "issues_found": results["issues_found"],
        "would_fix": results["would_fix"],
        "no_fix_available": results["no_fix_available"],
        "already_valid": results["already_valid"],
        "issue_types": dict(results["issue_types"]),
        "city_changes": {k: v for k, v in results["city_changes"].items()},
        "sample_fixes": results["sample_fixes"],
        "unfixable_samples": results["unfixable_samples"],
    }

    # Save to file
    output_file = "scripts/analysis/city_fix_preview.json"
    with open(output_file, 'w') as f:
        json.dump(results_json, f, indent=2)

    print(f"📁 Detailed results saved to: {output_file}")
    print()
    print("=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print()
    print("1. Review the preview results above")
    print("2. Check the detailed JSON file for complete list of changes")
    print("3. If satisfied, run: python3 scripts/fixes/fix_city_from_canonical.py")
    print()
    print("⚠️  Remember: Raw data is backed up and safe!")
    print()


if __name__ == "__main__":
    main()
