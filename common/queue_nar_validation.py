"""
Queue NAR Validation

Helper module to queue properties for NAR validation.

This module is called AFTER RealTrack ingestion to queue new properties
for background validation by the NAR validation service.

Usage:
    from common.queue_nar_validation import queue_property_for_validation

    # After inserting a property
    queue_property_for_validation(property_id, priority=5)

Date: 2025-10-03
"""

from typing import Optional, List
from .db import connect_with_retries


def queue_property_for_validation(
    property_id: str,
    priority: int = 5
) -> bool:
    """
    Queue a single property for NAR validation.

    Args:
        property_id: Property UUID
        priority: Priority (1 = highest, 10 = lowest), default: 5

    Returns:
        True if queued successfully, False otherwise
    """
    conn = connect_with_retries()
    cursor = conn.cursor()

    try:
        # Check if already queued
        cursor.execute("""
            SELECT id FROM nar_validation_queue
            WHERE property_id = %s
              AND status IN ('pending', 'processing')
        """, (property_id,))

        if cursor.fetchone():
            # Already queued, skip
            return True

        # Insert into queue
        cursor.execute("""
            INSERT INTO nar_validation_queue (
                property_id,
                priority,
                status
            )
            VALUES (%s, %s, 'pending')
        """, (property_id, priority))

        conn.commit()
        return True

    except Exception as e:
        print(f"Warning: Failed to queue property {property_id}: {e}")
        conn.rollback()
        return False

    finally:
        cursor.close()
        conn.close()


def queue_properties_batch(
    property_ids: List[str],
    priority: int = 5
) -> int:
    """
    Queue multiple properties for NAR validation (batch operation).

    Args:
        property_ids: List of property UUIDs
        priority: Priority (1 = highest, 10 = lowest), default: 5

    Returns:
        Number of properties successfully queued
    """
    if not property_ids:
        return 0

    conn = connect_with_retries()
    cursor = conn.cursor()

    try:
        # Check which properties are not already queued
        cursor.execute("""
            SELECT property_id
            FROM nar_validation_queue
            WHERE property_id = ANY(%s)
              AND status IN ('pending', 'processing')
        """, (property_ids,))

        already_queued = {row[0] for row in cursor.fetchall()}
        to_queue = [pid for pid in property_ids if pid not in already_queued]

        if not to_queue:
            return 0

        # Insert batch
        values = [(pid, priority) for pid in to_queue]

        cursor.executemany("""
            INSERT INTO nar_validation_queue (
                property_id,
                priority,
                status
            )
            VALUES (%s, %s, 'pending')
        """, values)

        conn.commit()
        return len(to_queue)

    except Exception as e:
        print(f"Warning: Failed to queue properties batch: {e}")
        conn.rollback()
        return 0

    finally:
        cursor.close()
        conn.close()


def get_queue_status() -> dict:
    """
    Get current validation queue status.

    Returns:
        Dict with queue statistics
    """
    conn = connect_with_retries()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                status,
                COUNT(*) as count
            FROM nar_validation_queue
            GROUP BY status
        """)

        rows = cursor.fetchall()
        status = {row[0]: row[1] for row in rows}

        return {
            'pending': status.get('pending', 0),
            'processing': status.get('processing', 0),
            'completed': status.get('completed', 0),
            'failed': status.get('failed', 0),
            'total': sum(status.values())
        }

    finally:
        cursor.close()
        conn.close()
