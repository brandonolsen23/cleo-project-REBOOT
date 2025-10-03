#!/usr/bin/env python3
"""
Address Matching Analysis Script

This script analyzes how well brand_locations and transaction properties
are matching up in the database, identifying potential gaps in address matching.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from collections import defaultdict
import json

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_properties():
    """Analyze properties table for brand and transaction linkage"""
    print("\n" + "="*80)
    print("PROPERTIES TABLE ANALYSIS")
    print("="*80)

    # Total properties
    result = supabase.table('properties').select('id', count='exact').execute()
    total_properties = result.count
    print(f"\nTotal properties in database: {total_properties:,}")

    # Properties in ON province
    result = supabase.table('properties').select('id', count='exact').eq('province', 'ON').execute()
    on_properties = result.count
    print(f"Properties in ON province: {on_properties:,}")

    # Properties with transactions (via transaction.property_id)
    result = supabase.table('transactions').select('property_id', count='exact').not_.is_('property_id', 'null').execute()
    properties_with_txns = result.count
    print(f"\nProperties with transactions: {properties_with_txns:,}")

    # Properties with brands (via property_brand_links)
    result = supabase.table('property_brand_links').select('property_id', count='exact').execute()
    properties_with_brands = result.count
    print(f"Property-brand links: {properties_with_brands:,}")

    # Get unique properties with brands
    result = supabase.rpc('get_properties_with_brands_count').execute() if False else None
    # Fallback: estimate unique properties with brands
    result = supabase.table('property_brand_links').select('property_id').limit(10000).execute()
    unique_properties_with_brands = len(set([link['property_id'] for link in result.data]))
    print(f"Unique properties with brands (sample): {unique_properties_with_brands:,}")

    return {
        'total': total_properties,
        'on_province': on_properties,
        'with_transactions': properties_with_txns,
        'with_brands_links': properties_with_brands,
        'with_brands_unique': unique_properties_with_brands
    }

def analyze_brand_locations():
    """Analyze brand_locations table"""
    print("\n" + "="*80)
    print("BRAND_LOCATIONS TABLE ANALYSIS")
    print("="*80)

    # Total brand locations
    result = supabase.table('brand_locations').select('id', count='exact').execute()
    total_locations = result.count
    print(f"\nTotal brand locations: {total_locations:,}")

    # Brand locations with property_id (matched)
    result = supabase.table('brand_locations').select('id', count='exact').not_.is_('property_id', 'null').execute()
    matched_locations = result.count
    print(f"Brand locations with property_id (matched): {matched_locations:,}")

    # Brand locations without property_id (unmatched)
    unmatched = total_locations - matched_locations
    print(f"Brand locations WITHOUT property_id (unmatched): {unmatched:,}")
    print(f"Match rate: {(matched_locations/total_locations*100):.1f}%")

    # Sample unmatched locations
    print("\nSample of unmatched brand_locations:")
    result = supabase.table('brand_locations').select('id, address_line1, city, province, postal_code, address_canonical').is_('property_id', 'null').limit(10).execute()
    for i, loc in enumerate(result.data[:5], 1):
        print(f"\n  {i}. Address: {loc.get('address_line1')}")
        print(f"     City: {loc.get('city')}, {loc.get('province')} {loc.get('postal_code')}")
        print(f"     Canonical: {loc.get('address_canonical')}")

    return {
        'total': total_locations,
        'matched': matched_locations,
        'unmatched': unmatched,
        'match_rate': matched_locations/total_locations*100
    }

def analyze_address_quality():
    """Analyze address quality and matching fields"""
    print("\n" + "="*80)
    print("ADDRESS QUALITY ANALYSIS")
    print("="*80)

    # Properties with address_canonical
    result = supabase.table('properties').select('id', count='exact').not_.is_('address_canonical', 'null').execute()
    props_with_canonical = result.count

    result = supabase.table('properties').select('id', count='exact').execute()
    total_props = result.count

    print(f"\nProperties with address_canonical: {props_with_canonical:,} / {total_props:,} ({props_with_canonical/total_props*100:.1f}%)")

    # Properties with address_hash
    result = supabase.table('properties').select('id', count='exact').not_.is_('address_hash', 'null').execute()
    props_with_hash = result.count
    print(f"Properties with address_hash: {props_with_hash:,} / {total_props:,} ({props_with_hash/total_props*100:.1f}%)")

    # Properties with geocoding (lat/long)
    result = supabase.table('properties').select('id', count='exact').not_.is_('latitude', 'null').execute()
    props_with_geocoding = result.count
    print(f"Properties with geocoding (lat/long): {props_with_geocoding:,} / {total_props:,} ({props_with_geocoding/total_props*100:.1f}%)")

    # Brand locations with address_canonical
    result = supabase.table('brand_locations').select('id', count='exact').not_.is_('address_canonical', 'null').execute()
    brands_with_canonical = result.count

    result = supabase.table('brand_locations').select('id', count='exact').execute()
    total_brands = result.count

    print(f"\nBrand locations with address_canonical: {brands_with_canonical:,} / {total_brands:,} ({brands_with_canonical/total_brands*100:.1f}%)")

    # Brand locations with address_hash
    result = supabase.table('brand_locations').select('id', count='exact').not_.is_('address_hash', 'null').execute()
    brands_with_hash = result.count
    print(f"Brand locations with address_hash: {brands_with_hash:,} / {total_brands:,} ({brands_with_hash/total_brands*100:.1f}%)")

    return {
        'properties': {
            'with_canonical': props_with_canonical,
            'with_hash': props_with_hash,
            'with_geocoding': props_with_geocoding,
            'total': total_props
        },
        'brand_locations': {
            'with_canonical': brands_with_canonical,
            'with_hash': brands_with_hash,
            'total': total_brands
        }
    }

def find_potential_matches():
    """Find potential matches that might have been missed"""
    print("\n" + "="*80)
    print("POTENTIAL MISSED MATCHES")
    print("="*80)

    print("\nLooking for brand_locations that might match existing properties...")

    # Get sample of unmatched brand locations with address_canonical
    result = supabase.table('brand_locations').select(
        'id, address_line1, city, province, postal_code, address_canonical, address_hash'
    ).is_('property_id', 'null').not_.is_('address_canonical', 'null').limit(100).execute()

    unmatched_brands = result.data
    print(f"\nAnalyzing {len(unmatched_brands)} unmatched brand locations...")

    potential_matches = []

    for brand_loc in unmatched_brands[:10]:  # Test first 10
        # Try to find matching property by address_hash
        if brand_loc.get('address_hash'):
            result = supabase.table('properties').select(
                'id, address_line1, city, province, postal_code, address_canonical'
            ).eq('address_hash', brand_loc['address_hash']).limit(1).execute()

            if result.data:
                potential_matches.append({
                    'brand_location': brand_loc,
                    'property': result.data[0],
                    'match_type': 'address_hash'
                })

    print(f"\nFound {len(potential_matches)} potential matches using address_hash")

    if potential_matches:
        print("\nSample potential matches:")
        for i, match in enumerate(potential_matches[:3], 1):
            print(f"\n  Match {i} (via {match['match_type']}):")
            print(f"    Brand Location: {match['brand_location']['address_line1']}, {match['brand_location']['city']}")
            print(f"    Property: {match['property']['address_line1']}, {match['property']['city']}")
            print(f"    Property ID: {match['property']['id']}")

    return potential_matches

def main():
    print("\n" + "="*80)
    print("DATABASE ADDRESS MATCHING ANALYSIS")
    print("="*80)

    results = {}

    # Run analyses
    results['properties'] = analyze_properties()
    results['brand_locations'] = analyze_brand_locations()
    results['address_quality'] = analyze_address_quality()
    results['potential_matches'] = find_potential_matches()

    # Summary and recommendations
    print("\n" + "="*80)
    print("SUMMARY & RECOMMENDATIONS")
    print("="*80)

    bl_data = results['brand_locations']
    print(f"\n📊 Current Match Rate: {bl_data['match_rate']:.1f}%")
    print(f"   - {bl_data['matched']:,} brand locations matched")
    print(f"   - {bl_data['unmatched']:,} brand locations unmatched")

    print("\n🔍 Potential Issues:")

    # Check address_hash coverage
    aq = results['address_quality']
    prop_hash_rate = aq['properties']['with_hash'] / aq['properties']['total'] * 100
    brand_hash_rate = aq['brand_locations']['with_hash'] / aq['brand_locations']['total'] * 100

    if prop_hash_rate < 95:
        print(f"   ⚠️  Only {prop_hash_rate:.1f}% of properties have address_hash")
    if brand_hash_rate < 95:
        print(f"   ⚠️  Only {brand_hash_rate:.1f}% of brand_locations have address_hash")

    print("\n💡 Recommendations:")
    print("   1. Run address canonicalization on all properties and brand_locations")
    print("   2. Generate address_hash for all records missing it")
    print("   3. Re-run address matching using updated hashes")
    print("   4. Consider fuzzy matching for addresses that don't hash match")
    print("   5. Implement geocoding for unmatched addresses to enable proximity matching")

    # Save results to file
    output_file = '/Users/brandonolsen23/Development/cleo-project-REBOOT/scripts/analysis/address_matching_results.json'
    with open(output_file, 'w') as f:
        json.dump({
            'properties': results['properties'],
            'brand_locations': results['brand_locations'],
            'address_quality': results['address_quality'],
            'potential_matches_count': len(results['potential_matches'])
        }, f, indent=2)

    print(f"\n📄 Full results saved to: {output_file}")

if __name__ == '__main__':
    main()
