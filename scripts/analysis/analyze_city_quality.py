#!/usr/bin/env python3
"""
City Data Quality Analysis

Analyzes the quality of city data to identify normalization issues.
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
from collections import Counter
import re

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_ANON_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_city_quality():
    """Analyze city data quality issues"""
    print("\n" + "="*80)
    print("CITY DATA QUALITY ANALYSIS")
    print("="*80)

    # Get all unique cities from properties
    result = supabase.table('properties').select('city').eq('province', 'ON').limit(20000).execute()

    cities = [prop['city'] for prop in result.data if prop.get('city')]

    print(f"\nTotal properties analyzed: {len(cities)}")
    print(f"Unique city values: {len(set(cities))}")

    # Identify issues
    issues = {
        'has_parentheses': [],
        'has_unit_number': [],
        'has_digits': [],
        'has_street_keywords': [],
        'too_long': [],
        'has_comma': [],
        'has_postal_code': []
    }

    street_keywords = ['street', 'st', 'road', 'rd', 'avenue', 'ave', 'blvd', 'boulevard',
                       'drive', 'dr', 'lane', 'ln', 'way', 'court', 'ct', 'place', 'pl',
                       'crescent', 'cres', 'circle', 'terrace']

    for city in set(cities):
        if not city:
            continue

        city_lower = city.lower()

        # Check for parentheses (sub-municipalities)
        if '(' in city or ')' in city:
            issues['has_parentheses'].append(city)

        # Check for unit numbers
        if re.search(r'\bunit\b|\bu\b|#\d+', city_lower):
            issues['has_unit_number'].append(city)

        # Check for excessive digits (might be street number or postal code)
        if re.search(r'\d{3,}', city):
            issues['has_digits'].append(city)

        # Check for street keywords
        if any(keyword in city_lower for keyword in street_keywords):
            issues['has_street_keywords'].append(city)

        # Check length (city names shouldn't be super long)
        if len(city) > 40:
            issues['too_long'].append(city)

        # Check for commas (indicates full address)
        if ',' in city:
            issues['has_comma'].append(city)

        # Check for postal code pattern
        if re.search(r'[A-Z]\d[A-Z]\s*\d[A-Z]\d', city):
            issues['has_postal_code'].append(city)

    # Print results
    print("\n" + "="*80)
    print("ISSUES FOUND")
    print("="*80)

    for issue_type, cities_with_issue in issues.items():
        if cities_with_issue:
            print(f"\n{issue_type.upper().replace('_', ' ')}: {len(cities_with_issue)} cities")
            print("Sample:")
            for city in sorted(cities_with_issue)[:10]:
                print(f"  - {city}")

    # Analyze city duplicates (base name variations)
    print("\n" + "="*80)
    print("CITY DUPLICATES (BASE NAME VARIATIONS)")
    print("="*80)

    # Find cities with parentheses and their base names
    city_groups = {}
    for city in set(cities):
        if not city:
            continue
        # Extract base name (remove parentheses content)
        base_name = re.sub(r'\s*\([^)]*\)', '', city).strip()
        if base_name not in city_groups:
            city_groups[base_name] = []
        city_groups[base_name].append(city)

    # Show groups with multiple variations
    duplicates = {k: v for k, v in city_groups.items() if len(v) > 1}
    print(f"\nFound {len(duplicates)} cities with multiple variations")
    print("\nTop duplicate groups:")
    for base_name, variations in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
        print(f"\n  {base_name} ({len(variations)} variations):")
        for var in sorted(variations):
            count = cities.count(var)
            print(f"    - {var} ({count} properties)")

    # Most common cities
    print("\n" + "="*80)
    print("MOST COMMON CITIES (TOP 20)")
    print("="*80)
    city_counts = Counter(cities)
    for city, count in city_counts.most_common(20):
        print(f"  {city}: {count} properties")

    return issues, duplicates

def sample_bad_addresses():
    """Sample properties with bad city data"""
    print("\n" + "="*80)
    print("SAMPLE PROPERTIES WITH BAD CITY DATA")
    print("="*80)

    # Get properties with unit numbers in city
    result = supabase.table('properties').select(
        'id, address_line1, city, province, postal_code, address_canonical'
    ).eq('province', 'ON').ilike('city', '%unit%').limit(5).execute()

    print("\nProperties with 'unit' in city field:")
    for prop in result.data:
        print(f"\n  ID: {prop['id']}")
        print(f"  Address Line 1: {prop.get('address_line1')}")
        print(f"  City: {prop.get('city')}")
        print(f"  Canonical: {prop.get('address_canonical')}")

    # Get properties with digits in city
    result = supabase.table('properties').select(
        'id, address_line1, city, province, postal_code, address_canonical'
    ).eq('province', 'ON').or_('city.like.%0%,city.like.%1%,city.like.%2%,city.like.%3%').limit(5).execute()

    print("\n\nProperties with digits in city field (sample):")
    for prop in result.data[:5]:
        city = prop.get('city', '')
        if re.search(r'\d', city):
            print(f"\n  ID: {prop['id']}")
            print(f"  Address Line 1: {prop.get('address_line1')}")
            print(f"  City: {city}")
            print(f"  Canonical: {prop.get('address_canonical')}")

def main():
    issues, duplicates = analyze_city_quality()
    sample_bad_addresses()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    total_issues = sum(len(v) for v in issues.values())
    print(f"\n🚨 Total unique city values with issues: {total_issues}")
    print(f"📊 City name variations (duplicates): {len(duplicates)}")

    print("\n💡 ROOT CAUSES:")
    print("   1. City field contains sub-municipality names (e.g., 'Toronto (Scarborough)')")
    print("   2. City field contains unit numbers (e.g., 'Unit #24')")
    print("   3. City field contains full street addresses")
    print("   4. Inconsistent handling of amalgamated cities (Toronto, Hamilton, Ottawa, etc.)")

    print("\n⚠️  IMPACT:")
    print("   - Address matching will fail for same address with different city variations")
    print("   - address_hash will be different for 'Toronto' vs 'Toronto (Scarborough)'")
    print("   - Users see duplicate/invalid cities in filter dropdowns")
    print("   - Impossible to properly aggregate data by city")

if __name__ == '__main__':
    main()
