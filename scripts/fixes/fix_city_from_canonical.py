#!/usr/bin/env python3
"""
Fix City Fields from Canonical Addresses
Applies the validated city corrections and re-computes address hashes.

This script:
1. Loads the preview results from preview_city_fixes.py
2. Applies the approved city corrections to properties table
3. Re-computes address_hash_raw for all corrected properties
4. Logs all changes to an audit file

Date: 2025-10-03
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List

import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.address import hash_address_raw
from common.address_parser import parse_and_validate_city
from common.db import connect_with_service_role


def load_preview_results() -> Dict:
    """Load the preview analysis results."""
    preview_file = "scripts/analysis/city_fix_preview.json"

    if not os.path.exists(preview_file):
        print(f"❌ Preview file not found: {preview_file}")
        print("   Please run: python3 scripts/analysis/preview_city_fixes.py first")
        sys.exit(1)

    with open(preview_file, 'r') as f:
        return json.load(f)


def apply_city_fixes(cur, dry_run: bool = False) -> Dict:
    """
    Apply city corrections to properties table.

    Returns:
        Dict with statistics about fixes applied
    """

    print("Fetching properties that need fixes...")
    cur.execute("""
        SELECT
            id,
            address_line1,
            city,
            city_backup,
            address_canonical,
            province,
            address_hash_raw
        FROM properties
        ORDER BY id
    """)

    properties = cur.fetchall()
    total_count = len(properties)
    print(f"✅ Loaded {total_count:,} properties\n")

    # Stats
    stats = {
        "properties_analyzed": total_count,
        "properties_fixed": 0,
        "properties_skipped": 0,
        "hash_recomputed": 0,
        "fixes_by_type": {},
        "sample_changes": []  # Only keep first 100 for audit
    }

    print("Analyzing fixes...\n")

    # Collect all updates to batch them
    updates_batch = []

    for i, prop in enumerate(properties):
        if i % 1000 == 0 and i > 0:
            print(f"  Progress: {i:,} / {total_count:,} ({i/total_count*100:.1f}%)")

        prop_id = prop['id']
        current_city = prop['city']
        canonical = prop['address_canonical']
        current_hash = prop['address_hash_raw']

        # Try to get a better city
        fixed_city = parse_and_validate_city(
            address=prop['address_line1'] or "",
            city_raw=current_city or "",
            province=prop['province'] or "ON",
            canonical=canonical
        )

        # Skip if no fix available or already correct
        if not fixed_city or fixed_city == current_city:
            stats["properties_skipped"] += 1
            continue

        # We have a fix!
        stats["properties_fixed"] += 1

        # Track change type
        change_key = f"{current_city} → {fixed_city}"
        stats["fixes_by_type"][change_key] = stats["fixes_by_type"].get(change_key, 0) + 1

        # Re-compute address hash with corrected city
        new_hash = hash_address_raw(prop['address_line1'], fixed_city)

        # Log first 100 changes as samples
        if len(stats["sample_changes"]) < 100:
            stats["sample_changes"].append({
                "property_id": prop_id,
                "address": prop['address_line1'],
                "old_city": current_city,
                "new_city": fixed_city,
                "old_hash": current_hash,
                "new_hash": new_hash,
            })

        # Add to batch
        if not dry_run:
            updates_batch.append((fixed_city, new_hash, prop_id))

    print(f"\n✅ Analysis complete!\n")

    # Apply batch updates if not dry run
    if not dry_run and updates_batch:
        print(f"Applying {len(updates_batch):,} updates in batches...")

        batch_size = 500
        for i in range(0, len(updates_batch), batch_size):
            batch = updates_batch[i:i + batch_size]

            # Use executemany for batch updates
            cur.executemany("""
                UPDATE properties
                SET
                    city = %s,
                    address_hash_raw = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, batch)

            stats["hash_recomputed"] += len(batch)

            if (i + batch_size) % 5000 == 0:
                print(f"  Applied {i + len(batch):,} / {len(updates_batch):,} updates")

        print(f"✅ All {len(updates_batch):,} updates applied\n")

    return stats


def print_summary(stats: Dict, dry_run: bool = False):
    """Print human-readable summary of changes."""

    mode = "DRY RUN" if dry_run else "APPLIED CHANGES"

    print("=" * 70)
    print(f"CITY FIX SUMMARY - {mode}")
    print("=" * 70)
    print()

    print(f"📊 Overall Stats:")
    print(f"   Properties analyzed:  {stats['properties_analyzed']:,}")
    print(f"   Properties fixed:     {stats['properties_fixed']:,}")
    print(f"   Properties skipped:   {stats['properties_skipped']:,}")
    print(f"   Hashes recomputed:    {stats['hash_recomputed']:,}")
    print()

    if stats['properties_fixed'] > 0:
        print(f"🔄 Fixes Applied by Type:")
        sorted_fixes = sorted(stats['fixes_by_type'].items(), key=lambda x: x[1], reverse=True)
        for change, count in sorted_fixes[:20]:  # Top 20
            print(f"   {change:50s} ({count:,} properties)")
        print()

        if len(sorted_fixes) > 20:
            print(f"   ... and {len(sorted_fixes) - 20} more fix types")
            print()

    print("=" * 70)
    print()


def save_audit_log(stats: Dict, dry_run: bool = False):
    """Save audit log to file."""

    mode = "dry_run" if dry_run else "applied"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    audit_file = f"scripts/fixes/city_fix_audit_{mode}_{timestamp}.json"

    with open(audit_file, 'w') as f:
        json.dump(stats, f, indent=2)

    print(f"📁 Audit log saved to: {audit_file}")
    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Apply city corrections from canonical addresses")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    parser.add_argument("--apply", action="store_true", help="Apply changes to database")
    parser.add_argument("--skip-confirmation", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Error: Must specify either --dry-run or --apply")
        print()
        print("Usage:")
        print("  python3 scripts/fixes/fix_city_from_canonical.py --dry-run   # Preview changes")
        print("  python3 scripts/fixes/fix_city_from_canonical.py --apply     # Apply changes")
        sys.exit(1)

    dry_run = args.dry_run

    print("=" * 70)
    if dry_run:
        print("CITY FIX - DRY RUN MODE")
    else:
        print("CITY FIX - APPLYING CHANGES")
    print("=" * 70)
    print()

    if not dry_run and not args.skip_confirmation:
        print("⚠️  WARNING: This will modify the database!")
        print("   - City fields will be updated")
        print("   - Address hashes will be recomputed")
        print()
        print("   Raw data is safely backed up in:")
        print("   - properties.city_backup")
        print("   - transactions.city_raw_backup")
        print()
        response = input("   Continue? (yes/no): ")
        if response.lower() != "yes":
            print("\n❌ Aborted by user")
            sys.exit(0)
        print()

    # Connect to database
    try:
        conn = connect_with_service_role()
        print("✅ Connected to database\n")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Apply fixes
                stats = apply_city_fixes(cur, dry_run=dry_run)

                if not dry_run:
                    # Commit changes
                    conn.commit()
                    print("✅ Changes committed to database\n")
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        if not dry_run:
            conn.rollback()
            print("   Changes rolled back")
        raise
    finally:
        conn.close()

    # Print summary
    print_summary(stats, dry_run=dry_run)

    # Save audit log
    save_audit_log(stats, dry_run=dry_run)

    if dry_run:
        print("=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print()
        print("1. Review the dry run results above")
        print("2. Check the audit log file for complete details")
        print("3. If satisfied, run with --apply flag:")
        print("   python3 scripts/fixes/fix_city_from_canonical.py --apply")
        print()
    else:
        print("=" * 70)
        print("✅ SUCCESS: City fixes applied!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Run validation script to verify results")
        print("2. Check city dropdown in UI - should show clean data")
        print("3. Review audit log for complete change history")
        print()
        print("To rollback if needed:")
        print("  UPDATE properties SET city = city_backup;")
        print()


if __name__ == "__main__":
    main()
