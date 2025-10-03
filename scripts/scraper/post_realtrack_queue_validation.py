#!/usr/bin/env python3
"""
Post-RealTrack Queue NAR Validation

This script should be called AFTER realtrack_ingest.py completes.
It queues all new properties for NAR validation.

Usage:
    # After RealTrack ingestion
    python3 scripts/scraper/post_realtrack_queue_validation.py

Or add to realtrack_ingest.py at the end:
    # Queue new properties for NAR validation
    subprocess.run(['python3', 'scripts/scraper/post_realtrack_queue_validation.py'])

Date: 2025-10-03
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.db import connect_with_retries
from common.queue_nar_validation import queue_properties_batch, get_queue_status


def queue_recent_properties(hours_back: int = 24):
    """
    Queue recently created properties for NAR validation.

    Args:
        hours_back: Queue properties created in last N hours (default: 24)
    """
    print("=" * 70)
    print("POST-REALTRACK - QUEUE NAR VALIDATION")
    print("=" * 70)
    print(f"  Queuing properties created in last {hours_back} hours...")
    print()

    conn = connect_with_retries()
    cursor = conn.cursor()

    try:
        # Find recent properties not yet queued
        cutoff_time = datetime.now() - timedelta(hours=hours_back)

        cursor.execute("""
            SELECT p.id
            FROM properties p
            LEFT JOIN nar_validation_queue q ON p.id = q.property_id
            WHERE p.created_at >= %s
              AND q.id IS NULL
        """, (cutoff_time,))

        property_ids = [row[0] for row in cursor.fetchall()]

        if not property_ids:
            print("✅ No new properties to queue")
            print()
            return

        print(f"📦 Found {len(property_ids)} new properties")

        # Queue in batches
        queued = queue_properties_batch(property_ids, priority=5)

        print(f"   ✅ Queued {queued} properties for validation")
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

    finally:
        cursor.close()
        conn.close()

    print("=" * 70)
    print("QUEUEING COMPLETE")
    print("=" * 70)
    print()
    print("✅ Properties queued for NAR validation")
    print("   The background service will process them automatically")
    print()


if __name__ == "__main__":
    # Default: queue properties from last 24 hours
    hours = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    queue_recent_properties(hours_back=hours)
