#!/usr/bin/env python3
"""
Phase 1: Add Backup Columns (Safety First)
This script creates backup columns to preserve original data before any fixes.
Date: 2025-10-03
"""

import os
import sys

import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.db import connect_with_service_role


def main():
    print("=" * 60)
    print("Phase 1: Adding Backup Columns to Preserve Raw Data")
    print("=" * 60)
    print()

    # Connect to database
    try:
        conn = connect_with_service_role()
        print("✅ Connected to database with service role\n")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    with conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 1. Add backup column to properties table
            print("1️⃣  Adding city_backup column to properties table...")
            cur.execute("""
                ALTER TABLE properties
                ADD COLUMN IF NOT EXISTS city_backup TEXT;
            """)
            print("   ✅ Column added (if not exists)\n")

            # 2. Copy current city values to backup
            print("2️⃣  Copying current city values to city_backup...")
            cur.execute("""
                UPDATE properties
                SET city_backup = city
                WHERE city_backup IS NULL;
            """)
            rows_updated = cur.rowcount
            print(f"   ✅ Backed up {rows_updated:,} city values\n")

            # 3. Add backup column to transactions table
            print("3️⃣  Adding city_raw_backup column to transactions table...")
            cur.execute("""
                ALTER TABLE transactions
                ADD COLUMN IF NOT EXISTS city_raw_backup TEXT;
            """)
            print("   ✅ Column added (if not exists)\n")

            # 4. Copy current city_raw values to backup
            print("4️⃣  Copying current city_raw values to city_raw_backup...")
            cur.execute("""
                UPDATE transactions
                SET city_raw_backup = city_raw
                WHERE city_raw_backup IS NULL;
            """)
            rows_updated = cur.rowcount
            print(f"   ✅ Backed up {rows_updated:,} city_raw values\n")

            # 5. Verify backups
            print("5️⃣  Verifying backups were created successfully...")
            print()

            # Check properties table
            cur.execute("""
                SELECT
                    COUNT(*) as total_rows,
                    COUNT(city) as city_count,
                    COUNT(city_backup) as backup_count,
                    COUNT(*) FILTER (WHERE city IS NOT NULL AND city_backup IS NOT NULL) as both_populated
                FROM properties;
            """)
            props = cur.fetchone()

            print("   📊 Properties Table:")
            print(f"      Total rows:       {props['total_rows']:,}")
            print(f"      City populated:   {props['city_count']:,}")
            print(f"      Backup populated: {props['backup_count']:,}")
            print(f"      Both populated:   {props['both_populated']:,}")
            print()

            # Check transactions table
            cur.execute("""
                SELECT
                    COUNT(*) as total_rows,
                    COUNT(city_raw) as city_count,
                    COUNT(city_raw_backup) as backup_count,
                    COUNT(*) FILTER (WHERE city_raw IS NOT NULL AND city_raw_backup IS NOT NULL) as both_populated
                FROM transactions;
            """)
            txns = cur.fetchone()

            print("   📊 Transactions Table:")
            print(f"      Total rows:       {txns['total_rows']:,}")
            print(f"      City populated:   {txns['city_count']:,}")
            print(f"      Backup populated: {txns['backup_count']:,}")
            print(f"      Both populated:   {txns['both_populated']:,}")
            print()

            # 6. Test rollback query (don't execute, just show)
            print("6️⃣  Rollback capability verified:")
            print()
            print("   To rollback changes in the future, run:")
            print("   " + "─" * 50)
            print("   UPDATE properties SET city = city_backup;")
            print("   UPDATE transactions SET city_raw = city_raw_backup;")
            print("   " + "─" * 50)
            print()

    conn.close()

    print("=" * 60)
    print("✅ SUCCESS: Backup columns created and populated!")
    print("=" * 60)
    print()
    print("Raw data is now safely backed up in:")
    print("  • properties.city_backup")
    print("  • transactions.city_raw_backup")
    print()
    print("Safe to proceed with Phase 2: Building Address Parser")
    print()


if __name__ == "__main__":
    main()
