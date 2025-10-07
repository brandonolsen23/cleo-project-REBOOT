"""
Parse transaction addresses and expand multi-property addresses
Populates transaction_address_expansion_parse table
"""
import os
import sys
import psycopg2

sys.path.insert(0, '/Users/brandonolsen23/Development/cleo-project-REBOOT')
from common.multi_property_parser import MultiPropertyAddressParser


def parse_transaction_addresses(limit=100):
    """Parse and expand transaction addresses"""

    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    print(f"Parsing transaction addresses (limit: {limit})...")
    print("=" * 100)

    # Get transactions that haven't been parsed yet
    cur.execute("""
        SELECT t.id, t.address_raw, t.city_raw
        FROM transactions t
        WHERE t.address_raw IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM transaction_address_expansion_parse p
                WHERE p.transaction_id = t.id
            )
        ORDER BY t.created_at DESC
        LIMIT %s
    """, (limit,))

    transactions = cur.fetchall()
    total = len(transactions)

    print(f"Found {total} transactions to parse\n")

    single_count = 0
    multi_count = 0
    total_expanded = 0

    for i, (tx_id, address_raw, city_raw) in enumerate(transactions, 1):
        print(f"[{i}/{total}] {address_raw}, {city_raw or 'NO CITY'}")

        # Parse with multi-property parser
        parsed = MultiPropertyAddressParser.parse(address_raw, city_raw)

        if parsed['is_multi_property']:
            multi_count += 1
            print(f"  ⚡ Multi-property ({parsed['pattern_type']}): {len(parsed['addresses'])} addresses")
        else:
            single_count += 1

        # Insert each expanded address
        for addr_data in parsed['addresses']:
            cur.execute("""
                INSERT INTO transaction_address_expansion_parse (
                    transaction_id,
                    original_address_raw,
                    original_city_raw,
                    is_multi_property,
                    pattern_type,
                    expanded_street_number,
                    expanded_street_name,
                    expanded_full_address,
                    address_position,
                    is_primary
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (transaction_id, expanded_full_address) DO NOTHING
            """, (
                tx_id,
                address_raw,
                city_raw,
                parsed['is_multi_property'],
                parsed['pattern_type'],
                addr_data['street_number'],
                addr_data['street'],
                addr_data['full_address'],
                addr_data['position'],
                addr_data['position'] == 1  # First is primary
            ))

            total_expanded += 1
            print(f"    [{addr_data['position']}] {addr_data['full_address']}")

        conn.commit()

    print("\n" + "=" * 100)
    print("PARSING COMPLETE")
    print("=" * 100)
    print(f"Transactions parsed: {total}")
    print(f"Single-property: {single_count} ({single_count*100/total:.1f}%)")
    print(f"Multi-property: {multi_count} ({multi_count*100/total:.1f}%)")
    print(f"Total expanded addresses: {total_expanded}")
    print(f"Additional addresses from expansion: {total_expanded - total}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Parse transaction addresses')
    parser.add_argument('--limit', type=int, default=100, help='Number of transactions to parse')
    args = parser.parse_args()

    parse_transaction_addresses(args.limit)
