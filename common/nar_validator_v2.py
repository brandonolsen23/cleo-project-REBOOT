"""
NAR Address Validator V2 - POSTAL CODE FIRST Strategy

This is a revised validator that prioritizes postal codes for city lookup.

Key improvements over V1:
1. Query by postal code ALONE to get city (95% confidence)
2. Then try to match full address for 100% confidence
3. Handle hyphenated address ranges ("3310 - 3350")
4. Handle address prefixes ("Quinte West 178 Front St")
5. Better confidence scoring

Date: 2025-10-03
"""

import os
import re
import duckdb
from datetime import datetime
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

from .db import connect_with_retries
from .ontario_cities import normalize_city


@dataclass
class NARValidationResult:
    """Result of NAR address validation."""

    # Match information
    nar_found: bool
    confidence_score: int  # 0-100

    # Validated address components
    city: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Match details
    match_type: Optional[str] = None
    source: str = "nar_query"

    def __repr__(self):
        return (
            f"NARValidationResult(found={self.nar_found}, "
            f"confidence={self.confidence_score}, "
            f"city={self.city}, match_type={self.match_type})"
        )


class NARValidatorV2:
    """
    NAR Address Validator V2 with Postal Code First strategy.

    Strategy:
    1. If postal code → Query NAR by postal code → Get city (95% confidence)
    2. Try to match full address too → 100% confidence if found
    3. If no postal code → Use address + city matching
    """

    def __init__(self, nar_parquet_path: Optional[str] = None):
        """
        Initialize NAR validator.

        Args:
            nar_parquet_path: Path to NAR parquet file
        """
        self.nar_parquet_path = nar_parquet_path or os.path.join(
            os.path.dirname(__file__),
            "..",
            "data/nar/addresses.geo.parquet"
        )

        if not os.path.exists(self.nar_parquet_path):
            raise FileNotFoundError(f"NAR parquet file not found: {self.nar_parquet_path}")

        self.duckdb_conn = None

    def _get_duckdb_connection(self):
        """Get or create DuckDB connection."""
        if self.duckdb_conn is None:
            self.duckdb_conn = duckdb.connect()
        return self.duckdb_conn

    def parse_street_number(self, address: str) -> Optional[str]:
        """
        Parse street number from address, handling ranges and prefixes.

        Examples:
            "3310 - 3350 STEELES AVE W" → "3310"
            "123 Main Street" → "123"
            "123A King St" → "123A"
            "Quinte West 178 Front St" → "178"

        Args:
            address: Full address string

        Returns:
            Street number or None if invalid
        """
        if not address:
            return None

        parts = address.strip().split()
        if not parts:
            return None

        # Remove city prefix (e.g., "Quinte West 178 Front St" → "178 Front St")
        # Look through parts to find the first one that starts with a digit or contains a hyphen range
        street_number_idx = 0

        for i, part in enumerate(parts):
            # Check if this part looks like a street number
            if part[0].isdigit() or (part[0] == '-' and len(part) > 1):
                street_number_idx = i
                break

        # Extract street number
        if street_number_idx >= len(parts):
            return None

        street_number = parts[street_number_idx]

        # Handle ranges (e.g., "3310-3350" or "3310 - 3350")
        # Check if current part contains hyphen, or if next part is "-"
        if '-' in street_number:
            # Split on hyphen and take first number
            range_parts = re.split(r'\s*-\s*', street_number)
            if range_parts:
                street_number = range_parts[0].strip()
        elif street_number_idx + 1 < len(parts) and parts[street_number_idx + 1] == '-':
            # Format is "3310 - 3350" (separate tokens)
            # Just use the first number
            pass  # street_number is already the first number

        return street_number if street_number else None

    def normalize_street_for_query(self, street: str) -> str:
        """
        Normalize street name for NAR query.

        Args:
            street: Street name

        Returns:
            Normalized street name
        """
        street_normalized = street.upper().strip()

        # Common abbreviations used in NAR
        abbreviations = {
            " STREET": " ST",
            " ROAD": " RD",
            " AVENUE": " AVE",
            " BOULEVARD": " BLVD",
            " DRIVE": " DR",
            " LANE": " LN",
            " COURT": " CT",
            " CRESCENT": " CRES",
            " PLACE": " PL",
            " TRAIL": " TRL",
            " WAY": " WAY",
            " CIRCLE": " CIR",
            " PARKWAY": " PKWY",
            " HIGHWAY": " HWY"
        }

        for full, abbr in abbreviations.items():
            street_normalized = street_normalized.replace(full, abbr)

        return street_normalized

    def query_by_postal_code(self, postal_code: str) -> Optional[Tuple[str, int]]:
        """
        Query NAR database by postal code ONLY to get city.

        Args:
            postal_code: Postal code (with or without spaces)

        Returns:
            Tuple of (city, address_count) or None if not found
        """
        con = self._get_duckdb_connection()

        # Clean postal code (remove spaces, uppercase)
        postal_clean = postal_code.strip().upper().replace(" ", "")

        if not postal_clean or len(postal_clean) < 6:
            return None

        query = f"""
            SELECT city, COUNT(*) as count
            FROM read_parquet('{self.nar_parquet_path}')
            WHERE country = 'CA'
              AND state = 'ON'
              AND REPLACE(UPPER(zipcode), ' ', '') = ?
            GROUP BY city
            ORDER BY count DESC
            LIMIT 1
        """

        result = con.execute(query, [postal_clean]).fetchone()

        if result:
            city, count = result
            return (city, count)

        return None

    def query_by_postal_and_address(
        self,
        street_number: str,
        street_name: str,
        postal_code: str
    ) -> Optional[Tuple[str, str, float, float]]:
        """
        Query NAR for specific address with postal code.

        Args:
            street_number: Street number
            street_name: Street name (normalized)
            postal_code: Postal code

        Returns:
            Tuple of (city, postal, lat, lon) or None
        """
        con = self._get_duckdb_connection()

        postal_clean = postal_code.strip().upper().replace(" ", "")

        query = f"""
            SELECT city, zipcode, latitude, longitude
            FROM read_parquet('{self.nar_parquet_path}')
            WHERE country = 'CA'
              AND state = 'ON'
              AND CAST(number AS VARCHAR) = ?
              AND UPPER(street) LIKE ?
              AND REPLACE(UPPER(zipcode), ' ', '') = ?
            LIMIT 1
        """

        result = con.execute(query, [street_number, f"%{street_name}%", postal_clean]).fetchone()

        if result:
            return result

        return None

    def query_by_address_and_city(
        self,
        street_number: str,
        street_name: str,
        city: str
    ) -> Optional[Tuple[str, str, float, float]]:
        """
        Query NAR by address and city.

        Args:
            street_number: Street number
            street_name: Street name (normalized)
            city: City name (normalized)

        Returns:
            Tuple of (city, postal, lat, lon) or None
        """
        con = self._get_duckdb_connection()

        query = f"""
            SELECT city, zipcode, latitude, longitude
            FROM read_parquet('{self.nar_parquet_path}')
            WHERE country = 'CA'
              AND state = 'ON'
              AND CAST(number AS VARCHAR) = ?
              AND UPPER(street) LIKE ?
              AND UPPER(city) = ?
            LIMIT 1
        """

        result = con.execute(query, [street_number, f"%{street_name}%", city]).fetchone()

        if result:
            return result

        return None

    def validate(
        self,
        address: str,
        city_hint: Optional[str] = None,
        postal_code: Optional[str] = None
    ) -> NARValidationResult:
        """
        Validate an address against NAR database.

        NEW STRATEGY (Postal Code First):
        1. If postal_code → Query by postal alone → 95% confidence
        2. Try to match full address too → 100% confidence
        3. If no postal → Use address + city → 90% confidence
        4. Fuzzy match → 70% confidence

        Args:
            address: Street address
            city_hint: City hint from source data (optional)
            postal_code: Postal code from source data (optional)

        Returns:
            Validation result with confidence score
        """
        # Handle None or empty address
        if not address:
            return NARValidationResult(
                nar_found=False,
                confidence_score=0,
                match_type="invalid_address",
                source="nar_query"
            )

        # Parse address
        street_number = self.parse_street_number(address)
        if not street_number:
            return NARValidationResult(
                nar_found=False,
                confidence_score=0,
                match_type="invalid_address",
                source="nar_query"
            )

        # Extract street name (everything after the street number)
        address_upper = address.strip().upper()
        parts = address_upper.split()

        # Find where the street number is in the parts
        street_number_idx = 0
        for i, part in enumerate(parts):
            if part.replace('-', '').replace(' ', '').startswith(street_number.replace('-', '').replace(' ', '')):
                street_number_idx = i
                break

        # Street name is everything after the street number (and the hyphen range if present)
        # Handle "3310 - 3350 STEELES" format
        start_idx = street_number_idx + 1
        if start_idx < len(parts) and parts[start_idx] == '-':
            # Skip the hyphen and the second number
            start_idx += 2

        street_name = ' '.join(parts[start_idx:]) if start_idx < len(parts) else ""
        street_name_normalized = self.normalize_street_for_query(street_name)

        # STRATEGY 1: Postal Code First!
        if postal_code and postal_code.strip():
            # Level 1: Query by postal code ONLY
            postal_result = self.query_by_postal_code(postal_code)

            if postal_result:
                city_from_postal, address_count = postal_result

                # Level 2: Try to find exact address too
                address_result = self.query_by_postal_and_address(
                    street_number,
                    street_name_normalized,
                    postal_code
                )

                if address_result:
                    # Perfect match! Address + postal code found
                    city, postal, lat, lon = address_result
                    return NARValidationResult(
                        nar_found=True,
                        confidence_score=100,
                        city=normalize_city(city),
                        postal_code=postal,
                        latitude=lat,
                        longitude=lon,
                        match_type="postal_and_address",
                        source="nar_query"
                    )
                else:
                    # Postal code found, but not the specific address
                    # Still trust the postal code for city!
                    return NARValidationResult(
                        nar_found=True,
                        confidence_score=95,
                        city=normalize_city(city_from_postal),
                        postal_code=postal_code,  # Use the postal code we have
                        latitude=None,
                        longitude=None,
                        match_type="postal_only",
                        source="nar_query"
                    )

        # STRATEGY 2: Address + City (no postal code)
        if city_hint:
            city_normalized = normalize_city(city_hint)

            result = self.query_by_address_and_city(
                street_number,
                street_name_normalized,
                city_normalized
            )

            if result:
                city, postal, lat, lon = result
                return NARValidationResult(
                    nar_found=True,
                    confidence_score=90,
                    city=normalize_city(city),
                    postal_code=postal,
                    latitude=lat,
                    longitude=lon,
                    match_type="address_and_city",
                    source="nar_query"
                )

        # STRATEGY 3: Fuzzy match (address only)
        con = self._get_duckdb_connection()

        query = f"""
            SELECT city, zipcode, latitude, longitude
            FROM read_parquet('{self.nar_parquet_path}')
            WHERE country = 'CA'
              AND state = 'ON'
              AND CAST(number AS VARCHAR) = ?
              AND UPPER(street) LIKE ?
            LIMIT 1
        """

        result = con.execute(query, [street_number, f"%{street_name_normalized}%"]).fetchone()

        if result:
            city, postal, lat, lon = result
            return NARValidationResult(
                nar_found=True,
                confidence_score=70,
                city=normalize_city(city),
                postal_code=postal,
                latitude=lat,
                longitude=lon,
                match_type="fuzzy",
                source="nar_query"
            )

        # No match found
        return NARValidationResult(
            nar_found=False,
            confidence_score=0,
            match_type="not_found",
            source="nar_query"
        )

    def close(self):
        """Close DuckDB connection."""
        if self.duckdb_conn:
            self.duckdb_conn.close()
            self.duckdb_conn = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
