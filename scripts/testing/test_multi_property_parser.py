"""
Test the multi-property address parser
"""
import sys
sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')
from common.multi_property_parser import MultiPropertyAddressParser

# Test cases from your actual data
test_addresses = [
    # Ampersand pattern
    ("471 & 481 KING ST E", "Kitchener"),
    ("944 & 952 QUEEN ST W", "Toronto"),
    ("3250 & 3300 BLOOR ST W", "Etobicoke"),

    # Range dash pattern
    ("9220 - 9226 HWY 93", "Midland"),
    ("1899 - 1923 IRONOAK WAY", "Oakville"),
    ("516 - 528 MAIN ST W", "Hawkesbury"),

    # Comma separated pattern
    ("10, 20 & 30 BROADLEAF AVE", "Whitby"),
    ("17, 19 & 29 BEECHWOOD AVE", "Ottawa"),

    # Single property (should not be parsed)
    ("140 ROGERS RD", "York"),
    ("804 OLD HWY 24", "Townsend"),
]

print("=" * 100)
print("MULTI-PROPERTY ADDRESS PARSER - TEST RESULTS")
print("=" * 100)

for address_raw, city in test_addresses:
    print(f"\n{'='*100}")
    print(f"INPUT: {address_raw}, {city}")
    print(f"{'='*100}")

    # Check if multi-property
    is_multi = MultiPropertyAddressParser.is_multi_property(address_raw)
    print(f"Is multi-property: {is_multi}")

    # Parse
    result = MultiPropertyAddressParser.parse(address_raw, city)

    print(f"\nParse result:")
    print(f"  Pattern type: {result['pattern_type']}")
    print(f"  Original address: {result['original_address']}")
    print(f"  Number of addresses: {len(result['addresses'])}")

    print(f"\n  Expanded addresses:")
    for addr in result['addresses']:
        print(f"    [{addr['position']}] {addr['full_address']}")
        print(f"        Street number: {addr['street_number']}")
        print(f"        Street: {addr['street']}")

print("\n" + "=" * 100)
print("SUMMARY")
print("=" * 100)

total = len(test_addresses)
multi_count = sum(1 for addr, _ in test_addresses if MultiPropertyAddressParser.is_multi_property(addr))
single_count = total - multi_count

print(f"Total test addresses: {total}")
print(f"Multi-property: {multi_count}")
print(f"Single property: {single_count}")

# Calculate total expanded addresses
total_expanded = 0
for address_raw, city in test_addresses:
    result = MultiPropertyAddressParser.parse(address_raw, city)
    total_expanded += len(result['addresses'])

print(f"\nOriginal addresses: {total}")
print(f"Expanded addresses: {total_expanded}")
print(f"Additional geocoding calls needed: {total_expanded - total}")
