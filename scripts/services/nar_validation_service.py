#!/usr/bin/env python3
"""
NAR Validation Background Service

This service:
1. Polls nar_validation_queue table for pending properties
2. Processes properties in batches of 100
3. Validates addresses against NAR database
4. Updates properties table with validated data (high confidence only)
5. Tracks statistics and performance
6. Sends email alerts on failures

Usage:
    python3 scripts/services/nar_validation_service.py

Run in background with screen:
    screen -S nar-validator
    python3 scripts/services/nar_validation_service.py
    # Press Ctrl+A, then D to detach

Check status:
    screen -r nar-validator

Date: 2025-10-03
"""

import os
import sys
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.db import connect_with_retries
from common.nar_validator import NARValidator


class NARValidationService:
    """
    Background service for NAR address validation.

    Polls validation queue and processes properties in batches.
    """

    def __init__(
        self,
        batch_size: int = 100,
        poll_interval_sec: int = 30,
        high_confidence_threshold: int = 90,
        enable_email_alerts: bool = True
    ):
        """
        Initialize validation service.

        Args:
            batch_size: Number of properties to process per batch (default: 100)
            poll_interval_sec: Seconds to wait between polls (default: 30)
            high_confidence_threshold: Minimum confidence to update property (default: 90)
            enable_email_alerts: Whether to send email alerts on failures (default: True)
        """
        self.batch_size = batch_size
        self.poll_interval_sec = poll_interval_sec
        self.high_confidence_threshold = high_confidence_threshold
        self.enable_email_alerts = enable_email_alerts

        # Performance tracking
        self.consecutive_failures = 0
        self.last_successful_batch = datetime.now()
        self.total_processed = 0
        self.total_updated = 0

        # Email alert settings (from environment)
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")
        self.alert_email = os.getenv("ALERT_EMAIL", self.smtp_user)

        print("=" * 70)
        print("NAR VALIDATION SERVICE - STARTING")
        print("=" * 70)
        print(f"  Batch size: {self.batch_size}")
        print(f"  Poll interval: {self.poll_interval_sec}s")
        print(f"  High confidence threshold: {self.high_confidence_threshold}%")
        print(f"  Email alerts: {self.enable_email_alerts}")
        print()

    def send_email_alert(self, subject: str, body: str):
        """
        Send email alert for service failures.

        Args:
            subject: Email subject
            body: Email body
        """
        if not self.enable_email_alerts:
            return

        if not all([self.smtp_user, self.smtp_pass, self.alert_email]):
            print(f"⚠️  Email alert disabled: SMTP credentials not configured")
            return

        try:
            msg = MIMEText(body)
            msg['Subject'] = f"[NAR Validator] {subject}"
            msg['From'] = self.smtp_user
            msg['To'] = self.alert_email

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)

            print(f"📧 Email alert sent: {subject}")

        except Exception as e:
            print(f"⚠️  Failed to send email alert: {e}")

    def fetch_batch(self) -> List[Dict]:
        """
        Fetch next batch of properties from validation queue.

        Returns:
            List of property records to validate
        """
        conn = connect_with_retries()
        cursor = conn.cursor()

        try:
            # Fetch pending properties, prioritized by priority and queued_at
            cursor.execute(f"""
                SELECT
                    q.id as queue_id,
                    q.property_id,
                    p.address_line1,
                    p.city,
                    p.postal_code,
                    p.address_canonical
                FROM nar_validation_queue q
                JOIN properties p ON q.property_id = p.id
                WHERE q.status = 'pending'
                ORDER BY q.priority ASC, q.queued_at ASC
                LIMIT {self.batch_size}
            """)

            rows = cursor.fetchall()

            # Convert to list of dicts
            batch = []
            for row in rows:
                batch.append({
                    'queue_id': row[0],
                    'property_id': row[1],
                    'address': row[2],
                    'city': row[3],
                    'postal_code': row[4],
                    'canonical': row[5]
                })

            return batch

        finally:
            cursor.close()
            conn.close()

    def mark_processing(self, queue_ids: List[str]):
        """
        Mark properties as processing in queue.

        Args:
            queue_ids: List of queue record IDs
        """
        if not queue_ids:
            return

        conn = connect_with_retries()
        cursor = conn.cursor()

        try:
            cursor.execute(f"""
                UPDATE nar_validation_queue
                SET status = 'processing',
                    attempts = attempts + 1,
                    last_attempt_at = NOW()
                WHERE id = ANY(%s)
            """, (queue_ids,))

            conn.commit()

        finally:
            cursor.close()
            conn.close()

    def update_property(
        self,
        property_id: str,
        validated_city: Optional[str],
        validated_postal: Optional[str],
        latitude: Optional[float],
        longitude: Optional[float],
        confidence_score: int
    ) -> Dict[str, bool]:
        """
        Update property with validated data (high confidence only).

        Args:
            property_id: Property UUID
            validated_city: Validated city from NAR
            validated_postal: Validated postal code from NAR
            latitude: Geocoding latitude
            longitude: Geocoding longitude
            confidence_score: Confidence score (0-100)

        Returns:
            Dict with flags for what was updated
        """
        updates = {
            'city_updated': False,
            'postal_updated': False,
            'geocoding_updated': False
        }

        if confidence_score < self.high_confidence_threshold:
            return updates

        conn = connect_with_retries()
        cursor = conn.cursor()

        try:
            # Always update city if high confidence
            if validated_city:
                cursor.execute("""
                    UPDATE properties
                    SET city = %s
                    WHERE id = %s
                """, (validated_city, property_id))
                updates['city_updated'] = True

            # Update postal code only when high confidence
            if validated_postal and confidence_score >= self.high_confidence_threshold:
                cursor.execute("""
                    UPDATE properties
                    SET postal_code = %s
                    WHERE id = %s
                """, (validated_postal, property_id))
                updates['postal_updated'] = True

            # Update geocoding only when high confidence
            if latitude and longitude and confidence_score >= self.high_confidence_threshold:
                cursor.execute("""
                    UPDATE properties
                    SET latitude = %s,
                        longitude = %s
                    WHERE id = %s
                """, (latitude, longitude, property_id))
                updates['geocoding_updated'] = True

            conn.commit()

        except Exception as e:
            print(f"⚠️  Failed to update property {property_id}: {e}")
            conn.rollback()

        finally:
            cursor.close()
            conn.close()

        return updates

    def mark_completed(
        self,
        queue_id: str,
        nar_found: bool,
        confidence_score: int,
        city_before: Optional[str],
        city_after: Optional[str],
        postal_before: Optional[str],
        postal_after: Optional[str],
        geocoding_updated: bool
    ):
        """
        Mark queue item as completed.

        Args:
            queue_id: Queue record ID
            nar_found: Whether address was found in NAR
            confidence_score: Confidence score
            city_before: City before validation
            city_after: City after validation
            postal_before: Postal code before
            postal_after: Postal code after
            geocoding_updated: Whether geocoding was updated
        """
        conn = connect_with_retries()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE nar_validation_queue
                SET status = 'completed',
                    validated_at = NOW(),
                    completed_at = NOW(),
                    nar_found = %s,
                    confidence_score = %s,
                    city_before = %s,
                    city_after = %s,
                    postal_code_before = %s,
                    postal_code_after = %s,
                    geocoding_updated = %s,
                    last_error = NULL
                WHERE id = %s
            """, (
                nar_found,
                confidence_score,
                city_before,
                city_after,
                postal_before,
                postal_after,
                geocoding_updated,
                queue_id
            ))

            conn.commit()

        finally:
            cursor.close()
            conn.close()

    def mark_failed(self, queue_id: str, error_message: str):
        """
        Mark queue item as failed.

        Args:
            queue_id: Queue record ID
            error_message: Error message
        """
        conn = connect_with_retries()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE nar_validation_queue
                SET status = 'failed',
                    last_error = %s,
                    last_attempt_at = NOW()
                WHERE id = %s
            """, (error_message, queue_id))

            conn.commit()

        finally:
            cursor.close()
            conn.close()

    def process_batch(self, batch: List[Dict], validator: NARValidator):
        """
        Process a batch of properties.

        Args:
            batch: List of property records
            validator: NAR validator instance
        """
        if not batch:
            return

        print(f"📦 Processing batch of {len(batch)} properties...")

        # Mark all as processing
        queue_ids = [item['queue_id'] for item in batch]
        self.mark_processing(queue_ids)

        batch_start_time = time.time()
        batch_updated = 0

        for item in batch:
            try:
                # Validate address
                result = validator.validate(
                    address=item['address'],
                    city_hint=item['city'],
                    postal_code=item['postal_code']
                )

                # Update property if high confidence
                updates = self.update_property(
                    property_id=item['property_id'],
                    validated_city=result.city,
                    validated_postal=result.postal_code,
                    latitude=result.latitude,
                    longitude=result.longitude,
                    confidence_score=result.confidence_score
                )

                if any(updates.values()):
                    batch_updated += 1

                # Mark as completed
                self.mark_completed(
                    queue_id=item['queue_id'],
                    nar_found=result.nar_found,
                    confidence_score=result.confidence_score,
                    city_before=item['city'],
                    city_after=result.city,
                    postal_before=item['postal_code'],
                    postal_after=result.postal_code,
                    geocoding_updated=updates['geocoding_updated']
                )

                self.total_processed += 1

            except Exception as e:
                error_msg = f"Validation error: {str(e)[:500]}"
                self.mark_failed(item['queue_id'], error_msg)
                print(f"⚠️  Failed to validate property {item['property_id']}: {e}")

        batch_elapsed = time.time() - batch_start_time

        self.total_updated += batch_updated
        self.last_successful_batch = datetime.now()
        self.consecutive_failures = 0

        print(f"   ✅ Completed {len(batch)} properties in {batch_elapsed:.1f}s")
        print(f"   📊 Updated: {batch_updated}, Cache hit rate: ~{(batch_updated / len(batch) * 100):.1f}%")
        print()

    def update_daily_stats(self):
        """Update daily statistics table."""
        conn = connect_with_retries()
        cursor = conn.cursor()

        try:
            today = datetime.now().date()

            cursor.execute("""
                INSERT INTO nar_validation_stats (
                    date,
                    total_validated,
                    nar_found,
                    nar_not_found,
                    high_confidence,
                    medium_confidence,
                    low_confidence,
                    cache_hits,
                    cache_misses,
                    cities_updated,
                    postal_codes_updated,
                    geocoding_updated
                )
                SELECT
                    %s,
                    COUNT(*),
                    COUNT(*) FILTER (WHERE nar_found = true),
                    COUNT(*) FILTER (WHERE nar_found = false),
                    COUNT(*) FILTER (WHERE confidence_score >= 90),
                    COUNT(*) FILTER (WHERE confidence_score BETWEEN 70 AND 89),
                    COUNT(*) FILTER (WHERE confidence_score < 70),
                    0, -- cache stats need separate tracking
                    0,
                    COUNT(*) FILTER (WHERE city_before != city_after),
                    COUNT(*) FILTER (WHERE postal_code_before != postal_code_after),
                    COUNT(*) FILTER (WHERE geocoding_updated = true)
                FROM nar_validation_queue
                WHERE DATE(completed_at) = %s
                  AND status = 'completed'
                ON CONFLICT (date)
                DO UPDATE SET
                    total_validated = EXCLUDED.total_validated,
                    nar_found = EXCLUDED.nar_found,
                    nar_not_found = EXCLUDED.nar_not_found,
                    high_confidence = EXCLUDED.high_confidence,
                    medium_confidence = EXCLUDED.medium_confidence,
                    low_confidence = EXCLUDED.low_confidence,
                    cities_updated = EXCLUDED.cities_updated,
                    postal_codes_updated = EXCLUDED.postal_codes_updated,
                    geocoding_updated = EXCLUDED.geocoding_updated
            """, (today, today))

            conn.commit()

        except Exception as e:
            print(f"⚠️  Failed to update daily stats: {e}")
            conn.rollback()

        finally:
            cursor.close()
            conn.close()

    def check_health(self):
        """
        Check service health and send alerts if needed.

        Alerts on:
        - 3 consecutive failures
        - 1 hour idle time (no successful batches)
        """
        # Check consecutive failures
        if self.consecutive_failures >= 3:
            subject = "Service Failure Alert"
            body = f"""
NAR Validation Service has failed {self.consecutive_failures} consecutive times.

Last successful batch: {self.last_successful_batch}
Total processed: {self.total_processed}
Total updated: {self.total_updated}

Please check the service logs and restart if needed.
            """
            self.send_email_alert(subject, body)
            self.consecutive_failures = 0  # Reset after alert

        # Check idle time
        idle_time = datetime.now() - self.last_successful_batch
        if idle_time > timedelta(hours=1):
            subject = "Service Idle Alert"
            body = f"""
NAR Validation Service has been idle for {idle_time.total_seconds() / 3600:.1f} hours.

Last successful batch: {self.last_successful_batch}
Total processed: {self.total_processed}
Total updated: {self.total_updated}

The validation queue may be empty, or the service may be stuck.
            """
            self.send_email_alert(subject, body)

    def run(self):
        """
        Main service loop.

        Continuously polls queue and processes batches.
        """
        print("🚀 Service started")
        print(f"   Polling every {self.poll_interval_sec}s for new properties...")
        print()

        validator = NARValidator(enable_cache=True)

        try:
            while True:
                # Fetch next batch
                batch = self.fetch_batch()

                if batch:
                    self.process_batch(batch, validator)
                else:
                    print(f"💤 Queue empty - waiting {self.poll_interval_sec}s...")

                # Update daily stats periodically
                if self.total_processed % 100 == 0 and self.total_processed > 0:
                    self.update_daily_stats()

                # Check health
                self.check_health()

                # Wait before next poll
                time.sleep(self.poll_interval_sec)

        except KeyboardInterrupt:
            print()
            print("=" * 70)
            print("SERVICE STOPPED")
            print("=" * 70)
            print(f"  Total processed: {self.total_processed}")
            print(f"  Total updated: {self.total_updated}")
            print()

        finally:
            validator.close()


if __name__ == "__main__":
    service = NARValidationService(
        batch_size=100,
        poll_interval_sec=30,
        high_confidence_threshold=90,
        enable_email_alerts=True
    )

    service.run()
