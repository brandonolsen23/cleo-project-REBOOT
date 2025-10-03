#!/usr/bin/env python3
"""
Set up NAR Validation Layer Database Tables

This script:
1. Creates nar_address_cache table (caching layer)
2. Creates nar_validation_queue table (queue for background processing)
3. Creates nar_validation_stats table (monitoring)
4. Creates helper views and triggers
5. Verifies setup is correct

Date: 2025-10-03
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.db import connect_with_retries


def setup_nar_validation_tables():
    """Create all NAR validation tables and indexes."""

    print("=" * 70)
    print("NAR VALIDATION LAYER - DATABASE SETUP")
    print("=" * 70)
    print()

    # Read SQL file
    sql_file = os.path.join(os.path.dirname(__file__), 'create_nar_validation_tables.sql')

    if not os.path.exists(sql_file):
        print(f"❌ SQL file not found: {sql_file}")
        sys.exit(1)

    print(f"📄 Reading SQL from: {sql_file}")
    with open(sql_file, 'r') as f:
        sql = f.read()

    print(f"   ✅ Loaded {len(sql):,} characters of SQL\n")

    # Connect to database
    print("🔌 Connecting to database...")
    conn = connect_with_retries()
    cursor = conn.cursor()
    print("   ✅ Connected\n")

    # Execute SQL
    print("⚙️  Creating tables, indexes, views, and triggers...")
    try:
        cursor.execute(sql)
        conn.commit()
        print("   ✅ All tables created successfully\n")
    except Exception as e:
        print(f"   ❌ Error creating tables: {e}")
        conn.rollback()
        sys.exit(1)

    # Verify tables exist
    print("🔍 Verifying tables...")

    tables_to_check = [
        'nar_address_cache',
        'nar_validation_queue',
        'nar_validation_stats'
    ]

    for table_name in tables_to_check:
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = '{table_name}'
        """)
        count = cursor.fetchone()[0]

        if count == 1:
            print(f"   ✅ {table_name}")
        else:
            print(f"   ❌ {table_name} NOT FOUND")

    print()

    # Check indexes
    print("🔍 Verifying indexes...")

    cursor.execute("""
        SELECT tablename, indexname
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename IN ('nar_address_cache', 'nar_validation_queue', 'nar_validation_stats')
        ORDER BY tablename, indexname
    """)

    indexes = cursor.fetchall()
    print(f"   ✅ Found {len(indexes)} indexes:")
    for table, index in indexes:
        print(f"      • {table}: {index}")

    print()

    # Check views
    print("🔍 Verifying views...")

    cursor.execute("""
        SELECT table_name
        FROM information_schema.views
        WHERE table_schema = 'public'
          AND table_name LIKE 'v_%validation%'
        ORDER BY table_name
    """)

    views = cursor.fetchall()
    print(f"   ✅ Found {len(views)} views:")
    for (view_name,) in views:
        print(f"      • {view_name}")

    print()

    # Test queue summary view
    print("🔍 Testing queue summary view...")

    cursor.execute("SELECT * FROM v_validation_queue_summary")
    rows = cursor.fetchall()

    if rows:
        print(f"   ✅ View works (found {len(rows)} status groups)")
    else:
        print(f"   ✅ View works (queue is empty)")

    print()

    # Summary
    print("=" * 70)
    print("SETUP COMPLETE")
    print("=" * 70)
    print()
    print("✅ Created tables:")
    print("   • nar_address_cache (caching layer)")
    print("   • nar_validation_queue (background processing)")
    print("   • nar_validation_stats (monitoring)")
    print()
    print(f"✅ Created {len(indexes)} indexes for fast lookups")
    print(f"✅ Created {len(views)} utility views")
    print()
    print("🚀 Next Steps:")
    print("   1. Build NARValidator class (common/nar_validator.py)")
    print("   2. Build background service (scripts/services/nar_validation_service.py)")
    print("   3. Add queue insertion hook to RealTrack ingestion")
    print()

    cursor.close()
    conn.close()


if __name__ == "__main__":
    setup_nar_validation_tables()
