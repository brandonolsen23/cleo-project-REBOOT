#!/usr/bin/env python3
"""
NAR Validation Service - Status Monitor

Shows real-time status of the NAR validation service:
- Queue status (pending, processing, completed, failed)
- Recent validations
- Cache performance
- Daily statistics
- Service health

Usage:
    python3 scripts/monitoring/nar_validation_status.py

    # Watch mode (refresh every 5 seconds)
    watch -n 5 python3 scripts/monitoring/nar_validation_status.py

Date: 2025-10-03
"""

import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.db import connect_with_retries


def get_queue_status():
    """Get current queue status."""
    conn = connect_with_retries()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                status,
                COUNT(*) as count,
                AVG(attempts) as avg_attempts,
                MIN(queued_at) as oldest,
                MAX(queued_at) as newest
            FROM nar_validation_queue
            GROUP BY status
        """)

        rows = cursor.fetchall()
        status = {}
        for row in rows:
            status[row[0]] = {
                'count': row[1],
                'avg_attempts': row[2] or 0,
                'oldest': row[3],
                'newest': row[4]
            }

        return status

    finally:
        cursor.close()
        conn.close()


def get_recent_validations(limit: int = 10):
    """Get recently completed validations."""
    conn = connect_with_retries()
    cursor = conn.cursor()

    try:
        cursor.execute(f"""
            SELECT
                p.address_line1,
                q.city_before,
                q.city_after,
                q.confidence_score,
                q.completed_at
            FROM nar_validation_queue q
            JOIN properties p ON q.property_id = p.id
            WHERE q.status = 'completed'
            ORDER BY q.completed_at DESC
            LIMIT {limit}
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


def get_cache_stats():
    """Get cache performance statistics."""
    conn = connect_with_retries()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                COUNT(*) as total_entries,
                SUM(lookup_count) as total_lookups,
                AVG(lookup_count) as avg_lookups,
                MAX(lookup_count) as max_lookups,
                COUNT(*) FILTER (WHERE lookup_count > 1) as reused_entries
            FROM nar_address_cache
        """)

        row = cursor.fetchone()

        if row and row[0]:
            return {
                'total_entries': row[0],
                'total_lookups': row[1],
                'avg_lookups': row[2],
                'max_lookups': row[3],
                'reused_entries': row[4],
                'reuse_rate': (row[4] / row[0] * 100) if row[0] > 0 else 0
            }
        else:
            return None

    finally:
        cursor.close()
        conn.close()


def get_daily_stats(days: int = 7):
    """Get daily statistics for last N days."""
    conn = connect_with_retries()
    cursor = conn.cursor()

    try:
        cursor.execute(f"""
            SELECT
                date,
                total_validated,
                nar_found,
                high_confidence,
                cities_updated,
                postal_codes_updated,
                geocoding_updated
            FROM nar_validation_stats
            WHERE date >= CURRENT_DATE - INTERVAL '{days} days'
            ORDER BY date DESC
        """)

        return cursor.fetchall()

    finally:
        cursor.close()
        conn.close()


def get_service_health():
    """Check service health indicators."""
    conn = connect_with_retries()
    cursor = conn.cursor()

    try:
        # Check for stuck processing items
        cursor.execute("""
            SELECT COUNT(*)
            FROM nar_validation_queue
            WHERE status = 'processing'
              AND last_attempt_at < NOW() - INTERVAL '5 minutes'
        """)
        stuck_count = cursor.fetchone()[0]

        # Check for failed items
        cursor.execute("""
            SELECT COUNT(*)
            FROM nar_validation_queue
            WHERE status = 'failed'
        """)
        failed_count = cursor.fetchone()[0]

        # Check last completed validation
        cursor.execute("""
            SELECT MAX(completed_at)
            FROM nar_validation_queue
            WHERE status = 'completed'
        """)
        last_completed = cursor.fetchone()[0]

        return {
            'stuck_count': stuck_count,
            'failed_count': failed_count,
            'last_completed': last_completed
        }

    finally:
        cursor.close()
        conn.close()


def print_status():
    """Print comprehensive service status."""
    print("=" * 80)
    print("NAR VALIDATION SERVICE - STATUS")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Queue Status
    print("📊 QUEUE STATUS")
    print("-" * 80)

    queue_status = get_queue_status()

    if queue_status:
        for status_name in ['pending', 'processing', 'completed', 'failed']:
            if status_name in queue_status:
                info = queue_status[status_name]
                print(f"  {status_name.upper():<12s} {info['count']:>8,} items")

                if status_name == 'pending' and info['oldest']:
                    age = datetime.now() - info['oldest']
                    print(f"               Oldest: {age.days}d {age.seconds // 3600}h ago")

                if status_name == 'failed':
                    print(f"               Avg attempts: {info['avg_attempts']:.1f}")
    else:
        print("  Queue is empty")

    print()

    # Service Health
    print("🏥 SERVICE HEALTH")
    print("-" * 80)

    health = get_service_health()

    if health['stuck_count'] > 0:
        print(f"  ⚠️  STUCK items: {health['stuck_count']} (processing > 5 min)")
    else:
        print(f"  ✅ No stuck items")

    if health['failed_count'] > 0:
        print(f"  ⚠️  FAILED items: {health['failed_count']}")
    else:
        print(f"  ✅ No failed items")

    if health['last_completed']:
        age = datetime.now() - health['last_completed']
        if age < timedelta(minutes=5):
            print(f"  ✅ Last validation: {age.seconds}s ago (ACTIVE)")
        elif age < timedelta(hours=1):
            print(f"  ⚠️  Last validation: {age.seconds // 60}m ago (IDLE)")
        else:
            print(f"  ❌ Last validation: {age.days}d {age.seconds // 3600}h ago (STOPPED?)")
    else:
        print(f"  ⚠️  No validations completed yet")

    print()

    # Cache Performance
    print("💾 CACHE PERFORMANCE")
    print("-" * 80)

    cache = get_cache_stats()

    if cache and cache['total_entries'] > 0:
        print(f"  Total cache entries:  {cache['total_entries']:>8,}")
        print(f"  Total lookups:        {cache['total_lookups']:>8,}")
        print(f"  Avg lookups/entry:    {cache['avg_lookups']:>8.1f}")
        print(f"  Reuse rate:           {cache['reuse_rate']:>7.1f}%")
        print(f"  Max lookups (1 addr): {cache['max_lookups']:>8,}")
    else:
        print("  Cache is empty")

    print()

    # Recent Validations
    print("🔄 RECENT VALIDATIONS (Last 10)")
    print("-" * 80)

    recent = get_recent_validations(limit=10)

    if recent:
        for row in recent:
            address, city_before, city_after, confidence, completed = row

            change_marker = "✅" if city_before != city_after else "  "
            print(f"  {change_marker} {address[:40]:<40s} {city_before or 'NULL':<15s} → {city_after or 'NULL':<15s} ({confidence:>3d}%)")
    else:
        print("  No validations completed yet")

    print()

    # Daily Statistics
    print("📈 DAILY STATISTICS (Last 7 Days)")
    print("-" * 80)
    print(f"  {'Date':<12s} {'Validated':>10s} {'Found':>8s} {'High Conf':>10s} {'Updated':>8s}")
    print("-" * 80)

    daily = get_daily_stats(days=7)

    if daily:
        for row in daily:
            date, total, found, high_conf, cities_updated, postal_updated, geo_updated = row
            total_updated = cities_updated + postal_updated + geo_updated
            print(f"  {str(date):<12s} {total:>10,} {found:>8,} {high_conf:>10,} {total_updated:>8,}")
    else:
        print("  No statistics available yet")

    print()
    print("=" * 80)
    print()


if __name__ == "__main__":
    print_status()
