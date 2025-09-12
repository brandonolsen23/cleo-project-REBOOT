#!/usr/bin/env python3
import argparse
import os
import sys
from typing import Optional

import psycopg2

from common.canonical import canonicalize_address, hash_canonical_address
from common.geocode import Geocoder


def get_db():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)
    return psycopg2.connect(url)


def standardize_one(cur, geocoder: Geocoder, pid: str, address_line1: Optional[str], city: Optional[str], province: Optional[str], country: Optional[str]):
    country = country or "CA"
    canonical = canonicalize_address(address_line1, city, province, country)
    address_hash = hash_canonical_address(address_line1, city, province, country)

    lat = lng = accuracy = None
    geocode_source = None
    if geocoder.available():
        result = geocoder.geocode(canonical, country=country)
        if result:
            loc = result.get("location") or {}
            lat = loc.get("lat")
            lng = loc.get("lng")
            accuracy = (result.get("accuracy"))
            geocode_source = "geocodio"
            comps = (result.get("address_components") or {})
            # backfill province/postal if missing
            province_new = comps.get("state")
            postal = comps.get("zip") or comps.get("postal_code")
            if province_new and (not province):
                province = province_new
            # update with geocoded city if missing
            city_new = comps.get("city")
            if city_new and (not city):
                city = city_new

    # Build geom WKT if lat/lng
    if lat is not None and lng is not None:
        cur.execute(
            """
            UPDATE properties
            SET address_canonical = $1,
                address_hash = $2,
                latitude = $3,
                longitude = $4,
                geocode_source = $5,
                geocode_accuracy = $6,
                city = COALESCE(city, $7),
                province = COALESCE(province, $8),
                country = COALESCE(country, $9),
                geom = ST_SetSRID(ST_MakePoint($4, $3), 4326)::geography
            WHERE id = $10
            """.replace("$", "%"),
            (canonical, address_hash, lat, lng, geocode_source, accuracy, city, province, country, pid),
        )
    else:
        # No coordinates; still set canonical + hash
        cur.execute(
            """
            UPDATE properties
            SET address_canonical = $1,
                address_hash = $2,
                city = COALESCE(city, $3),
                province = COALESCE(province, $4),
                country = COALESCE(country, $5)
            WHERE id = $6
            """.replace("$", "%"),
            (canonical, address_hash, city, province, country, pid),
        )


def main():
    ap = argparse.ArgumentParser(description="Standardize properties: canonical address, hash, geocode")
    ap.add_argument("--limit", type=int, default=100, help="Max properties to process")
    ap.add_argument("--country", default="CA", help="Default country code")
    ap.add_argument("--no-geocode", action="store_true", help="Skip live geocoding (compute canonical only)")
    args = ap.parse_args()

    geo = Geocoder() if not args.no_geocode else Geocoder(api_key=None)

    conn = get_db()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, address_line1, city, province, country
                FROM properties
                WHERE address_hash IS NULL
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (args.limit,),
            )
            rows = cur.fetchall()
            processed = 0
            for pid, addr1, city, prov, country in rows:
                try:
                    standardize_one(cur, geo, pid, addr1, city, prov, country or args.country)
                    processed += 1
                except Exception as e:
                    print(f"Failed to standardize {pid}: {e}", file=sys.stderr)
    conn.close()
    print(f"Standardized properties: {processed}")


if __name__ == "__main__":
    main()

