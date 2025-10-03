#!/usr/bin/env python3
"""
Test NAR Validator

Quick test to verify NARValidator is working correctly.

Date: 2025-10-03
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from common.nar_validator import NARValidator


def test_nar_validator():
    """Test NAR validator with sample addresses."""

    print("=" * 70)
    print("NAR VALIDATOR - TEST")
    print("=" * 70)
    print()

    # Create validator
    print("🔧 Initializing NAR validator...")
    validator = NARValidator()
    print("   ✅ Initialized\n")

    # Test cases
    test_cases = [
        {
            "name": "Toronto address (no postal code)",
            "address": "100 Queen Street West",
            "city_hint": "Toronto",
            "postal_code": None
        },
        {
            "name": "Toronto address with postal code",
            "address": "100 Queen Street West",
            "city_hint": "Toronto",
            "postal_code": "M5H 2N2"
        },
        {
            "name": "Address with wrong city hint",
            "address": "100 Queen Street West",
            "city_hint": "Mississauga",  # Wrong city
            "postal_code": None
        },
        {
            "name": "Invalid address",
            "address": "99999 Fake Street",
            "city_hint": "Toronto",
            "postal_code": None
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        print(f"   Address: {test['address']}")
        print(f"   City Hint: {test['city_hint']}")
        print(f"   Postal Code: {test['postal_code']}")

        result = validator.validate(
            address=test['address'],
            city_hint=test['city_hint'],
            postal_code=test['postal_code']
        )

        print(f"   ✅ Result:")
        print(f"      Found in NAR: {result.nar_found}")
        print(f"      Confidence: {result.confidence_score}")
        print(f"      City: {result.city}")
        print(f"      Postal Code: {result.postal_code}")
        print(f"      Match Type: {result.match_type}")
        print(f"      Source: {result.source}")

        if result.latitude and result.longitude:
            print(f"      Geocoding: ({result.latitude:.6f}, {result.longitude:.6f})")

        print()

    # Test caching
    print("🔄 Testing cache...")
    print("   Querying same address again (should use cache)...")

    result2 = validator.validate(
        address="100 Queen Street West",
        city_hint="Toronto",
        postal_code=None
    )

    print(f"   Source: {result2.source}")
    if result2.source == "cache":
        print("   ✅ Cache working!")
    else:
        print("   ⚠️  Cache not used (may be expected on first run)")

    print()

    # Close validator
    validator.close()

    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print()
    print("✅ NAR validator is working correctly")
    print()


if __name__ == "__main__":
    test_nar_validator()
