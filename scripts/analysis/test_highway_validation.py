"""
Test highway address validation strategy
Tests the 6 problematic HWY addresses with commercial POI detection
"""
import os
import sys
import psycopg2

sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')
from common.address_validator import AddressValidator


def test_highway_addresses():
    """Test validation on the 6 highway addresses"""

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    validator = AddressValidator()

    if not validator.available():
        print("❌ Google API key not found!")
        return

    print("Testing Highway Address Validation")
    print("=" * 100)

    # Get the 6 highway addresses that were problematic
    cur.execute("""
        SELECT
            p.id,
            p.expanded_full_address,
            p.original_address_raw,
            p.is_multi_property,
            p.pattern_type,
            g.google_postal_code,
            g.google_latitude,
            g.google_longitude,
            g.google_formatted_address
        FROM transaction_address_expansion_parse p
        JOIN google_geocoded_addresses g ON g.source_id = p.id
        WHERE g.source_table = 'transaction_address_expansion_parse'
            AND (p.expanded_full_address LIKE '%HWY%' OR p.expanded_full_address LIKE '%HIGHWAY%')
        ORDER BY p.original_address_raw, p.address_position
    """)

    addresses = cur.fetchall()
    total = len(addresses)

    print(f"Found {total} highway addresses to validate\n")

    # Group by original address for range validation
    from collections import defaultdict
    grouped = defaultdict(list)

    for addr_data in addresses:
        original = addr_data[2]  # original_address_raw
        grouped[original].append(addr_data)

    validation_results = []

    for original_addr, addr_list in grouped.items():
        print(f"\n{'='*100}")
        print(f"Original: {original_addr}")
        print(f"Expanded to {len(addr_list)} addresses")
        print(f"{'='*100}\n")

        # Check if this is a multi-property range
        is_multi = addr_list[0][3]  # is_multi_property
        pattern = addr_list[0][4]  # pattern_type

        if is_multi and pattern == 'range_dash' and len(addr_list) == 2:
            # Apply range validation
            start_data = addr_list[0]
            end_data = addr_list[1]

            start_addr = start_data[1]  # expanded_full_address
            end_addr = end_data[1]

            start_postal = start_data[5]
            end_postal = end_data[5]

            print(f"  RANGE VALIDATION:")
            print(f"  Start: {start_addr}")
            print(f"    Postal: {start_postal or 'NO POSTAL'}")

            print(f"  End: {end_addr}")
            print(f"    Postal: {end_postal or 'NO POSTAL'}")

            # Determine best address
            if start_postal and not end_postal:
                best = 'start'
                confidence = 90
                print(f"\n  ✓ RECOMMENDATION: Use START address (has postal code)")
            elif end_postal and not start_postal:
                best = 'end'
                confidence = 90
                print(f"\n  ✓ RECOMMENDATION: Use END address (has postal code)")
            elif start_postal and end_postal:
                if start_postal == end_postal:
                    best = 'both'
                    confidence = 100
                    print(f"\n  ✓ RECOMMENDATION: Both valid with same postal ({start_postal})")
                else:
                    best = 'conflict'
                    confidence = 50
                    print(f"\n  ⚠️ WARNING: Conflicting postal codes - manual review needed")
            else:
                best = 'neither'
                confidence = 0
                print(f"\n  ⚠️ WARNING: Neither has postal - checking commercial POIs...")

                # Check commercial activity for both
                for i, addr_data in enumerate([start_data, end_data]):
                    lat = addr_data[6]  # google_latitude
                    lng = addr_data[7]  # google_longitude
                    formatted = addr_data[8]  # google_formatted_address

                    if lat and lng:
                        print(f"\n  Checking {'START' if i == 0 else 'END'}: {formatted}")
                        poi_data = validator.check_commercial_activity(lat, lng, radius=200)
                        print(f"    POIs found: {poi_data['poi_count']}")
                        print(f"    Has retail: {poi_data['has_retail']}")
                        print(f"    Confidence boost: +{poi_data['confidence_boost']}")

                        if poi_data['poi_count'] >= 3:
                            confidence = 75
                            best = 'start' if i == 0 else 'end'
                            print(f"    ✓ Sufficient commercial activity - likely correct location")

            validation_results.append({
                'original': original_addr,
                'best': best,
                'confidence': confidence,
                'start_postal': start_postal,
                'end_postal': end_postal
            })

        else:
            # Single address or non-range multi-property
            for addr_data in addr_list:
                expanded = addr_data[1]
                postal = addr_data[5]
                lat = addr_data[6]
                lng = addr_data[7]
                formatted = addr_data[8]

                print(f"  Address: {expanded}")
                print(f"  Postal: {postal or 'NO POSTAL'}")

                if lat and lng:
                    print(f"  Checking commercial activity...")
                    poi_data = validator.check_commercial_activity(lat, lng, radius=200)
                    print(f"    POIs found: {poi_data['poi_count']}")
                    print(f"    Has retail: {poi_data['has_retail']}")
                    print(f"    Confidence boost: +{poi_data['confidence_boost']}")

                    if postal and poi_data['poi_count'] >= 3:
                        confidence = 100
                        print(f"    ✓ HIGH CONFIDENCE: Has postal + commercial activity")
                    elif postal:
                        confidence = 75
                        print(f"    ✓ MEDIUM CONFIDENCE: Has postal but low commercial activity")
                    elif poi_data['poi_count'] >= 3:
                        confidence = 65
                        print(f"    ⚠️ MEDIUM-LOW CONFIDENCE: No postal but commercial activity present")
                    else:
                        confidence = 25
                        print(f"    ⚠️ LOW CONFIDENCE: No postal and no commercial activity")

                    validation_results.append({
                        'original': original_addr,
                        'address': expanded,
                        'confidence': confidence,
                        'postal': postal,
                        'poi_count': poi_data['poi_count']
                    })

    # Summary
    print(f"\n\n{'='*100}")
    print("VALIDATION SUMMARY")
    print(f"{'='*100}\n")

    high_confidence = [r for r in validation_results if r.get('confidence', 0) >= 75]
    medium_confidence = [r for r in validation_results if 50 <= r.get('confidence', 0) < 75]
    low_confidence = [r for r in validation_results if r.get('confidence', 0) < 50]

    print(f"High confidence (≥75): {len(high_confidence)}")
    print(f"Medium confidence (50-74): {len(medium_confidence)}")
    print(f"Low confidence (<50): {len(low_confidence)}")

    if low_confidence:
        print(f"\n⚠️ LOW CONFIDENCE ADDRESSES REQUIRING REVIEW:")
        for result in low_confidence:
            print(f"  - {result.get('original', result.get('address'))}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    test_highway_addresses()
