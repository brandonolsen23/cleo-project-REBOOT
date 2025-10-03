#!/usr/bin/env python3
"""
Backfill NAR Validation for Existing Properties

Queues all existing properties for NAR validation.
Run this once to validate all 16k+ existing properties.

The background validation service will process them automatically.

Usage:
    python3 scripts/backfill/backfill_nar_validation.py

Options:
    --limit N      Limit to N properties (for testing)
    --priority P   Set priority (1-10, default: 5)

Date: 2025-10-03
"""

import os
import sys
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.db import connect_with_retries
from common.queue_nar_validation import queue_properties_batch, get_queue_status


def backfill_validation_queue(limit: int = None, priority: int = 5):
    """
    Queue all existing properties for NAR validation.

    Args:
        limit: Optional limit on number of properties to queue (for testing)
        priority: Priority level (1-10, default: 5)
    """
    print("=" * 70)
    print("BACKFILL NAR VALIDATION QUEUE")
    print("=" * 70)
    print(f"  Priority: {priority}")
    if limit:
        print(f"  Limit: {limit:,} properties (testing mode)")
    else:
        print(f"  Limit: None (queue ALL properties)")
    print()

    conn = connect_with_retries()
    cursor = conn.cursor()

    try:
        # Count total properties
        cursor.execute("SELECT COUNT(*) FROM properties")
        total_properties = cursor.fetchone()[0]
        print(f"📊 Total properties in database: {total_properties:,}")

        # Find properties not yet queued
        limit_clause = f"LIMIT {limit}" if limit else ""

        cursor.execute(f"""
            SELECT p.id
            FROM properties p
            LEFT JOIN nar_validation_queue q ON p.id = q.property_id
            WHERE q.id IS NULL
            {limit_clause}
        """)

        property_ids = [row[0] for row in cursor.fetchall()]

        if not property_ids:
            print("✅ All properties already queued!")
            print()
            return

        print(f"📦 Found {len(property_ids):,} properties to queue")
        print()

        # Queue in batches of 1000
        batch_size = 1000
        total_queued = 0

        for i in range(0, len(property_ids), batch_size):
            batch = property_ids[i:i + batch_size]
            queued = queue_properties_batch(batch, priority=priority)
            total_queued += queued

            progress = (i + len(batch)) / len(property_ids) * 100
            print(f"   [{progress:5.1f}%] Queued {total_queued:,} / {len(property_ids):,} properties...")

        print()
        print(f"✅ Queued {total_queued:,} properties for validation")
        print()

        # Show queue status
        status = get_queue_status()
        print("📊 Current Queue Status:")
        print(f"   Pending:    {status['pending']:,}")
        print(f"   Processing: {status['processing']:,}")
        print(f"   Completed:  {status['completed']:,}")
        print(f"   Failed:     {status['failed']:,}")
        print(f"   Total:      {status['total']:,}")
        print()

        # Estimate processing time
        batch_processing_time = 30  # seconds per batch of 100
        batches = status['pending'] / 100
        estimated_hours = (batches * batch_processing_time) / 3600

        print("⏱️  Estimated Processing Time:")
        print(f"   With batch size 100, ~30s/batch")
        print(f"   Total batches: {batches:.0f}")
        print(f"   Estimated time: {estimated_hours:.1f} hours")
        print()

    finally:
        cursor.close()
        conn.close()

    print("=" * 70)
    print("BACKFILL COMPLETE")
    print("=" * 70)
    print()
    print("✅ Properties queued for NAR validation")
    print("   The background service will process them automatically")
    print()
    print("🚀 Start the background service with:")
    print("   screen -S nar-validator")
    print("   python3 scripts/services/nar_validation_service.py")
    print()


def main():
    """Parse arguments and run backfill."""
    parser = argparse.ArgumentParser(
        description="Backfill NAR validation queue for existing properties"
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help="Limit number of properties to queue (for testing)"
    )

    parser.add_argument(
        '--priority',
        type=int,
        default=5,
        choices=range(1, 11),
        help="Priority level (1 = highest, 10 = lowest)"
    )

    args = parser.parse_args()

    backfill_validation_queue(
        limit=args.limit,
        priority=args.priority
    )


if __name__ == "__main__":
    main()
