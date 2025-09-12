#!/usr/bin/env python3
import argparse
import os
import sys
from typing import Optional

from common.canonical import canonicalize_address, hash_canonical_address
from common.geocode import Geocoder
from common.db import connect_with_retries


def get_db():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)
    return connect_with_retries(url, attempts=6, backoff_sec=1.5, prefer_pooler=True)


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
            SET address_canonical = %s,
                address_hash = %s,
                latitude = %s,
                longitude = %s,
                geocode_source = %s,
                geocode_accuracy = %s,
                city = COALESCE(city, %s),
                province = COALESCE(province, %s),
                country = COALESCE(country, %s),
                geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
            WHERE id = %s
            """,
            (canonical, address_hash, lat, lng, geocode_source, accuracy, city, province, country, lng, lat, pid),
        )
    else:
        # No coordinates; still set canonical + hash
        cur.execute(
            """
            UPDATE properties
            SET address_canonical = %s,
                address_hash = %s,
                city = COALESCE(city, %s),
                province = COALESCE(province, %s),
                country = COALESCE(country, %s)
            WHERE id = %s
            """,
            (canonical, address_hash, city, province, country, pid),
        )


def geocode_by_canonical(cur, geocoder: Geocoder, canonical: str, country: str = "CA") -> bool:
    result = geocoder.geocode(canonical, country=country)
    if not result:
        return False
    loc = result.get("location") or {}
    lat = loc.get("lat")
    lng = loc.get("lng")
    accuracy = result.get("accuracy")
    if lat is None or lng is None:
        return False
    cur.execute(
        """
        UPDATE properties
        SET latitude = %s,
            longitude = %s,
            geocode_source = 'geocodio',
            geocode_accuracy = %s,
            geom = ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
        WHERE address_canonical = %s AND latitude IS NULL
        """,
        (lat, lng, accuracy, lng, lat, canonical),
    )
    return True


def main():
    ap = argparse.ArgumentParser(description="Standardize properties: canonical address, hash, geocode in batches")
    ap.add_argument("--canonical-limit", type=int, default=1000, help="Max properties to canonicalize in this run")
    ap.add_argument("--geocode-limit", type=int, default=0, help="Max distinct canonical addresses to geocode in this run (0=use daily-quota)")
    ap.add_argument("--daily-quota", type=int, default=2500, help="API daily quota for geocoding (distinct canonicals)")
    ap.add_argument("--sleep-ms", type=int, default=200, help="Sleep between geocode calls to be polite")
    ap.add_argument("--country", default="CA", help="Default country code")
    ap.add_argument("--no-geocode", action="store_true", help="Skip live geocoding (compute canonical only)")
    args = ap.parse_args()

    geo = Geocoder() if not args.no_geocode else Geocoder(api_key=None)

    conn = get_db()
    with conn:
        with conn.cursor() as cur:
            # Phase A: canonicalize rows missing address_hash
            cur.execute(
                """
                SELECT id, address_line1, city, province, country
                FROM properties
                WHERE address_hash IS NULL
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (args.canonical_limit,),
            )
            rows = cur.fetchall()
            canon_count = 0
            for pid, addr1, city, prov, country in rows:
                try:
                    standardize_one(cur, geo, pid, addr1, city, prov, country or args.country)
                    canon_count += 1
                except Exception as e:
                    print(f"Failed to standardize {pid}: {e}", file=sys.stderr)

            # Phase B: geocode distinct canonical addresses (if enabled)
            geocode_done = 0
            if geo.available() and not args.no_geocode:
                quota = args.daily_quota if args.geocode_limit == 0 else args.geocode_limit
                cur.execute(
                    """
                    SELECT address_canonical
                    FROM properties
                    WHERE address_canonical IS NOT NULL AND latitude IS NULL
                    GROUP BY address_canonical
                    ORDER BY COUNT(*) DESC
                    LIMIT %s
                    """,
                    (quota,),
                )
                todo = [r[0] for r in cur.fetchall()]
                import time
                for canonical in todo:
                    try:
                        ok = geocode_by_canonical(cur, geo, canonical, country=args.country)
                        geocode_done += 1 if ok else 0
                    except Exception as e:
                        print(f"Failed to geocode '{canonical}': {e}", file=sys.stderr)
                    # be polite
                    time.sleep(max(0, args.sleep_ms) / 1000.0)
    conn.close()
    print(f"Canonicalized: {canon_count}. Geocoded distinct canonical addresses: {geocode_done}.")


if __name__ == "__main__":
    main()
