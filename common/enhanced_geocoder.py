"""
Enhanced Geocoder with Text Search Fallback
Uses Text Search API when Geocoding API returns low confidence results
"""
import os
import time
import requests
from typing import Optional, Dict, Any
from common.google_geocoder import GoogleGeocoder


class EnhancedGeocoder:
    """Enhanced geocoder with automatic fallback to Text Search for problematic addresses"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_GEOCODING_API_KEY")
        self.geocoder = GoogleGeocoder(api_key=self.api_key)
        self.text_search_url = "https://maps.googleapis.com/maps/api/place/textsearch/json"

    def geocode_with_fallback(self, address: str, region: str = "CA") -> Dict[str, Any]:
        """
        Geocode address with automatic fallback to Text Search if needed

        Returns:
        {
            'method': 'geocoding' | 'text_search',
            'confidence': int (0-100),
            'needs_review': bool,
            'formatted_address': str,
            'components': {...},
            'location': {'lat': float, 'lng': float},
            'place_id': str,
            'postal_code': str,
            'raw': dict
        }
        """
        # Try regular geocoding first
        geocode_result = self.geocoder.geocode(address, region=region)

        if not geocode_result:
            # Geocoding failed - try Text Search
            return self._fallback_to_text_search(address)

        # Check if result is low confidence
        components = geocode_result.get('components', {})
        postal = components.get('postal_code')
        formatted = geocode_result.get('formatted_address', '')

        # Low confidence indicators:
        # 1. No postal code
        # 2. Formatted address is just "City, Province, Country"
        is_low_confidence = (
            not postal or
            (formatted.count(',') <= 2 and not any(char.isdigit() for char in formatted.split(',')[0]))
        )

        if is_low_confidence:
            # Try Text Search fallback
            text_result = self._fallback_to_text_search(address)

            # If Text Search found postal code, use it
            if text_result.get('components', {}).get('postal_code'):
                text_result['needs_review'] = False  # Text Search fixed it
                return text_result
            else:
                # Both failed - flag for manual review
                geocode_result['needs_review'] = True
                geocode_result['confidence'] = 25
                return geocode_result
        else:
            # High confidence from geocoding
            geocode_result['needs_review'] = False
            return geocode_result

    def _fallback_to_text_search(self, address: str) -> Dict[str, Any]:
        """Use Places Text Search API as fallback"""
        params = {
            'key': self.api_key,
            'query': address,
            'region': 'ca'
        }

        try:
            response = requests.get(self.text_search_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get('status') == 'OK' and data.get('results'):
                result = data['results'][0]

                # Extract components from formatted address
                formatted_addr = result.get('formatted_address', '')
                location = result.get('geometry', {}).get('location', {})

                # Parse formatted address for components
                components = self._parse_formatted_address(formatted_addr)

                return {
                    'method': 'text_search',
                    'confidence': 90,  # Text Search is very accurate
                    'needs_review': False,
                    'formatted_address': formatted_addr,
                    'components': components,
                    'location': {
                        'lat': location.get('lat'),
                        'lng': location.get('lng')
                    },
                    'place_id': result.get('place_id'),
                    'postal_code': components.get('postal_code'),
                    'raw': result
                }
            else:
                return {
                    'method': 'text_search',
                    'confidence': 0,
                    'needs_review': True,
                    'formatted_address': None,
                    'components': {},
                    'location': {},
                    'place_id': None,
                    'postal_code': None,
                    'raw': data
                }

        except Exception as e:
            print(f"  ⚠️ Text Search error: {str(e)}")
            return {
                'method': 'text_search',
                'confidence': 0,
                'needs_review': True,
                'error': str(e)
            }

    def _parse_formatted_address(self, formatted_addr: str) -> Dict[str, str]:
        """Parse formatted address into components"""
        # Example: "9226 ON-93, Midland, ON L4R 4K4, Canada"
        parts = [p.strip() for p in formatted_addr.split(',')]

        components = {}

        if len(parts) >= 1:
            # First part usually has street number and name
            street_parts = parts[0].split()
            if street_parts and street_parts[0].isdigit():
                components['street_number'] = street_parts[0]
                components['street'] = ' '.join(street_parts[1:])

        if len(parts) >= 2:
            components['city'] = parts[1].strip()

        if len(parts) >= 3:
            # Province and postal code
            province_postal = parts[2].strip().split()
            if province_postal:
                components['province'] = province_postal[0]
                if len(province_postal) >= 2:
                    components['postal_code'] = ' '.join(province_postal[1:])

        return components

    def available(self) -> bool:
        """Check if API key is available"""
        return bool(self.api_key)
