#!/usr/bin/env python3
"""
Test libpostal parsing on sample addresses from our database.
Phase 1: Install & Test libpostal
"""

import json
import os
import sys

from postal.parser import parse_address

def test_libpostal():
    """Test libpostal on sample addresses"""

    # Load sample addresses
    with open('/tmp/sample_addresses.json', 'r') as f:
        addresses = json.load(f)

    print("=" * 100)
    print("LIBPOSTAL PARSING TEST - PHASE 1")
    print("=" * 100)
    print(f"Testing {len(addresses)} addresses\n")

    # Statistics
    stats = {
        'total': 0,
        'house_number_extracted': 0,
        'road_extracted': 0,
        'city_extracted': 0,
        'postcode_extracted': 0,
        'unit_extracted': 0,
        'hyphenated_detected': 0
    }

    for i, addr_data in enumerate(addresses, 1):
        source = addr_data['source']

        # Build full address string for parsing
        if source == 'transactions':
            # Transactions: Combine address_raw + city_raw
            full_address = f"{addr_data['address_raw']}, {addr_data['city_raw']}, ON, CA"
        else:
            # Brand locations: Use address + city + postal_code
            full_address = f"{addr_data['address']}, {addr_data['city']}, ON, {addr_data['postal_code']}, CA"

        print(f"\n{'='*100}")
        print(f"ADDRESS #{i} - Source: {source.upper()}")
        print(f"{'='*100}")
        print(f"Input: {full_address}")
        print(f"\n{'-'*100}")

        # Parse with libpostal
        try:
            parsed = parse_address(full_address)

            print("PARSED COMPONENTS:")
            print(f"{'-'*100}")

            # Display parsed components
            components = {}
            for component, label in parsed:
                components[label] = component
                print(f"  {label:20s} → {component}")

            # Update statistics
            stats['total'] += 1
            if 'house_number' in components:
                stats['house_number_extracted'] += 1
            if 'road' in components:
                stats['road_extracted'] += 1
            if 'city' in components:
                stats['city_extracted'] += 1
            if 'postcode' in components:
                stats['postcode_extracted'] += 1
            if 'unit' in components:
                stats['unit_extracted'] += 1

            # Check for hyphenated addresses
            if source == 'transactions' and '-' in addr_data['address_raw']:
                stats['hyphenated_detected'] += 1
                print(f"\n  ⚠️  HYPHENATED ADDRESS DETECTED: {addr_data['address_raw']}")
                print(f"      This will need range expansion in Phase 8")

            # Original data comparison
            print(f"\n{'-'*100}")
            print("ORIGINAL DATA (for comparison):")
            if source == 'transactions':
                print(f"  Address Raw: {addr_data['address_raw']}")
                print(f"  City Raw: {addr_data['city_raw']}")
            else:
                print(f"  Address: {addr_data['address']}")
                print(f"  City: {addr_data['city']}")
                print(f"  Postal Code: {addr_data['postal_code']}")

        except Exception as e:
            print(f"❌ ERROR parsing address: {e}")
            continue

    # Print summary statistics
    print("\n\n" + "="*100)
    print("PARSING STATISTICS - PHASE 1 SUCCESS CRITERIA")
    print("="*100)

    total = stats['total']
    print(f"\nTotal Addresses Parsed: {total}")
    print(f"\n{'Component':<25} {'Count':<10} {'Percentage':<15} {'Target':<15} {'Status'}")
    print("-"*100)

    def print_stat(name, count, target_pct):
        pct = (count / total * 100) if total > 0 else 0
        status = "✅ PASS" if pct >= target_pct else "❌ FAIL"
        print(f"{name:<25} {count:<10} {pct:>6.1f}%{'':<8} {target_pct:>6}%{'':<8} {status}")

    print_stat("House Number", stats['house_number_extracted'], 95)
    print_stat("Road/Street", stats['road_extracted'], 95)
    print_stat("City", stats['city_extracted'], 90)
    print_stat("Postal Code", stats['postcode_extracted'], 50)  # Lower target (not all have it)

    print(f"\n{'-'*100}")
    print(f"Unit Numbers Extracted: {stats['unit_extracted']}")
    print(f"Hyphenated Addresses Detected: {stats['hyphenated_detected']}")

    # Overall assessment
    print("\n" + "="*100)
    house_pct = (stats['house_number_extracted'] / total * 100) if total > 0 else 0
    road_pct = (stats['road_extracted'] / total * 100) if total > 0 else 0
    city_pct = (stats['city_extracted'] / total * 100) if total > 0 else 0

    if house_pct >= 95 and road_pct >= 95 and city_pct >= 90:
        print("✅ PHASE 1 SUCCESS: libpostal parsing quality meets criteria!")
        print("✅ Ready to proceed to Phase 2: Parse Transactions Table")
    else:
        print("❌ PHASE 1 INCOMPLETE: Parsing quality below target")
        print("   Review results and adjust approach if needed")

    print("="*100)

    return stats

if __name__ == '__main__':
    test_libpostal()
