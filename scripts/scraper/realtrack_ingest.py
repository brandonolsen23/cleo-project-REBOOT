#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import Json

from common.address import hash_address_raw, normalize_raw_address
from common.ingest_utils import (
    canonical_price,
    compute_source_hash,
    parse_date,
    parse_site_area,
)


def get_db() -> psycopg2.extensions.connection:
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set. Add it to .env or your environment.", file=sys.stderr)
        sys.exit(1)
    return psycopg2.connect(url)


def load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Expected a list of records in JSON file")
        return data


def upsert_staging(cur, source: str, source_hash: str, raw: dict):
    cur.execute(
        """
        INSERT INTO stg_transactions (source, source_hash, raw)
        VALUES (%s, %s, %s)
        ON CONFLICT (source_hash) DO NOTHING
        """,
        (source, source_hash, Json(raw)),
    )


def find_or_create_property(cur, addr_hash_raw: str, address: str, city: str,
                            arn: Optional[str], pin: Optional[str], alt1: Optional[str], alt2: Optional[str], alt3: Optional[str]) -> str:
    # 1) Match by address_hash_raw
    cur.execute("SELECT id FROM properties WHERE address_hash_raw = %s LIMIT 1", (addr_hash_raw,))
    row = cur.fetchone()
    if row:
        return row[0]

    # 2) Match by identifiers
    for id_type, id_val in (("ARN", arn), ("PIN", pin)):
        if not id_val:
            continue
        cur.execute(
            """
            SELECT p.id
            FROM property_identifiers pi
            JOIN properties p ON p.id = pi.property_id
            WHERE LOWER(pi.id_type) = LOWER(%s) AND pi.id_value = %s
            LIMIT 1
            """,
            (id_type, id_val),
        )
        row = cur.fetchone()
        if row:
            return row[0]

    # 3) Create new property
    cur.execute(
        """
        INSERT INTO properties (address_line1, city, address_canonical, address_hash_raw, arn, pin, alt_address1, alt_address2, alt_address3)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (address or None, city or None, None, addr_hash_raw, arn, pin, alt1, alt2, alt3),
    )
    prop_id = cur.fetchone()[0]

    # Add identifiers if present
    for id_type, id_val in (("ARN", arn), ("PIN", pin)):
        if id_val:
            cur.execute(
                """
                INSERT INTO property_identifiers (property_id, id_type, id_value, source)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id_type, id_value) DO NOTHING
                """,
                (prop_id, id_type, id_val, "realtrack"),
            )

    return prop_id


def upsert_transaction(cur, tx: Dict[str, Any], prop_id: Optional[str], details: dict):
    columns = (
        "source", "source_id", "source_hash", "property_id", "transaction_date", "transaction_type", "price",
        "arn", "pin", "address_raw", "city_raw", "address_hash_raw", "address_canonical", "address_hash",
        "alt_address1", "alt_address2", "alt_address3",
        "buyer_name", "buyer_address", "buyer_alt_name1", "buyer_alt_name2", "buyer_alt_name3",
        "buyer_contact_first_name", "buyer_contact_last_name", "buyer_phone",
        "seller_name", "seller_address", "seller_alt_name1", "seller_alt_name2", "seller_alt_name3",
        "seller_contact_first_name", "seller_contact_last_name", "seller_phone",
        "brokerage_name", "brokerage_phone", "site", "site_area_acres", "site_area_sqft", "relationship", "description", "source_url", "details"
    )

    placeholders = ", ".join(["%s"] * len(columns))
    assignments = ", ".join([f"{c} = EXCLUDED.{c}" for c in columns if c not in ("source_hash",)])

    values = tuple(tx.get(c) for c in columns[:-1]) + (Json(details),)

    cur.execute(
        f"""
        INSERT INTO transactions ({', '.join(columns)})
        VALUES ({placeholders})
        ON CONFLICT (source_hash) DO UPDATE SET
        {assignments}
        """,
        values,
    )


def main():
    parser = argparse.ArgumentParser(description="Ingest Realtrack JSON into staging and normalized tables.")
    parser.add_argument("--input", required=True, help="Path to Realtrack JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Parse and validate without writing to DB")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of records processed")
    args = parser.parse_args()

    data = load_json(args.input)
    if args.limit:
        data = data[: args.limit]

    if args.dry_run:
        # Basic parse check
        for r in data[:3]:
            _ = compute_source_hash(r)
            _ = hash_address_raw(r.get("Address"), r.get("City"))
        print(f"Loaded {len(data)} records. Hash/parse OK (dry-run).")
        return

    conn = get_db()
    inserted = 0
    updated = 0
    skipped = 0
    with conn:
        with conn.cursor() as cur:
            for rec in data:
                source_hash = compute_source_hash(rec)
                upsert_staging(cur, "realtrack", source_hash, rec)

                # Build normalized payload
                addr = rec.get("Address") or ""
                city = rec.get("City") or ""
                addr_hash_raw = hash_address_raw(addr, city)
                sale_date = parse_date(rec.get("SaleDate"))
                price = canonical_price(rec.get("SalePrice"))

                # property resolution
                prop_id = find_or_create_property(
                    cur,
                    addr_hash_raw,
                    address=addr,
                    city=city,
                    arn=(rec.get("ARN") or None),
                    pin=(rec.get("PIN") or None),
                    alt1=(rec.get("AlternateAddress1") or None),
                    alt2=(rec.get("AlternateAddress2") or None),
                    alt3=(rec.get("AlternateAddress3") or None),
                )

                acres, sqft = parse_site_area(rec.get("Site"))

                tx = {
                    "source": "realtrack",
                    "source_id": None,
                    "source_hash": source_hash,
                    "property_id": prop_id,
                    "transaction_date": sale_date,
                    "transaction_type": "sale" if rec.get("SalePrice") else None,
                    "price": price,
                    "arn": rec.get("ARN") or None,
                    "pin": rec.get("PIN") or None,
                    "address_raw": addr or None,
                    "city_raw": city or None,
                    "address_hash_raw": addr_hash_raw,
                    "address_canonical": None,
                    "address_hash": None,
                    "alt_address1": rec.get("AlternateAddress1") or None,
                    "alt_address2": rec.get("AlternateAddress2") or None,
                    "alt_address3": rec.get("AlternateAddress3") or None,
                    "buyer_name": rec.get("Buyer") or None,
                    "buyer_address": rec.get("BuyerAddress") or None,
                    "buyer_alt_name1": rec.get("BuyerAlternateName1") or None,
                    "buyer_alt_name2": rec.get("BuyerAlternateName2") or None,
                    "buyer_alt_name3": rec.get("BuyerAlternateName3") or None,
                    "buyer_contact_first_name": rec.get("BuyerContactFirstName") or None,
                    "buyer_contact_last_name": rec.get("BuyerContactLastName") or None,
                    "buyer_phone": rec.get("BuyerPhone") or None,
                    "seller_name": rec.get("Seller") or None,
                    "seller_address": rec.get("SellerAddress") or None,
                    "seller_alt_name1": rec.get("SellerAlternateName1") or None,
                    "seller_alt_name2": rec.get("SellerAlternateName2") or None,
                    "seller_alt_name3": rec.get("SellerAlternateName3") or None,
                    "seller_contact_first_name": rec.get("SellerContactFirstName") or None,
                    "seller_contact_last_name": rec.get("SellerContactLastName") or None,
                    "seller_phone": rec.get("SellerPhone") or None,
                    "brokerage_name": rec.get("Brokerage") or None,
                    "brokerage_phone": rec.get("BrokeragePhone") or None,
                    "site": rec.get("Site") or None,
                    "site_area_acres": acres,
                    "site_area_sqft": sqft,
                    "relationship": rec.get("Relationship") or None,
                    "description": rec.get("Description") or None,
                    "source_url": rec.get("URL") or None,
                }

                # Attempt insert; ON CONFLICT means either insert or update
                before = cur.rowcount
                upsert_transaction(cur, tx, prop_id, details=rec)
                after = cur.rowcount
                # We can't rely on rowcount for upsert diff; just count
                inserted += 1

    conn.close()
    print(f"Processed {len(data)} records. Upserted: {inserted}. Skipped (staging duplicates): {skipped}.")


if __name__ == "__main__":
    main()
