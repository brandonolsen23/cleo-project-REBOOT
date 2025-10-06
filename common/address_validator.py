"""
Address Validation with Commercial POI Detection
Validates geocoded addresses using Google Places API for commercial activity
"""
import os
import requests
import time
from typing import Optional, Dict, Any, List
from common.google_geocoder import GoogleGeocoder


class AddressValidator:
    """Validates geocoded addresses using commercial POI detection"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_GEOCODING_API_KEY")
        self.geocoder = GoogleGeocoder(api_key=self.api_key)
        self.places_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    def validate_range_address(self, start_addr: str, end_addr: str, city: str) -> Dict[str, Any]:
        """
        Validate range addresses by geocoding both endpoints

        Args:
            start_addr: e.g., "9220 HWY 93"
            end_addr: e.g., "9226 HWY 93"
            city: e.g., "Midland"

        Returns:
            {
                'best_address': str,
                'confidence': int (0-100),
                'start_result': dict,
                'end_result': dict,
                'recommendation': str
            }
        """
        # Geocode both with Ontario suffix
        start_input = f"{start_addr}, {city}, Ontario"
        end_input = f"{end_addr}, {city}, Ontario"

        start_geocode = self.geocoder.geocode(start_input)
        end_geocode = self.geocoder.geocode(end_input)

        # Extract postal codes
        start_postal = start_geocode.get('components', {}).get('postal_code') if start_geocode else None
        end_postal = end_geocode.get('components', {}).get('postal_code') if end_geocode else None

        # Decision logic
        if start_postal and not end_postal:
            return {
                'best_address': start_addr,
                'confidence': 90,
                'start_result': start_geocode,
                'end_result': end_geocode,
                'recommendation': 'Start address has postal code, end does not'
            }
        elif end_postal and not start_postal:
            return {
                'best_address': end_addr,
                'confidence': 90,
                'start_result': start_geocode,
                'end_result': end_geocode,
                'recommendation': 'End address has postal code, start does not'
            }
        elif start_postal and end_postal:
            if start_postal == end_postal:
                return {
                    'best_address': start_addr,
                    'confidence': 100,
                    'start_result': start_geocode,
                    'end_result': end_geocode,
                    'recommendation': 'Both have same postal code - using start address'
                }
            else:
                return {
                    'best_address': None,
                    'confidence': 50,
                    'start_result': start_geocode,
                    'end_result': end_geocode,
                    'recommendation': 'Conflicting postal codes - manual review needed'
                }
        else:
            # Neither has postal - escalate to POI check
            return {
                'best_address': None,
                'confidence': 0,
                'start_result': start_geocode,
                'end_result': end_geocode,
                'recommendation': 'Neither has postal code - check commercial POIs'
            }

    def check_commercial_activity(self, latitude: float, longitude: float,
                                   radius: int = 100) -> Dict[str, Any]:
        """
        Check for commercial POIs near a location

        Args:
            latitude, longitude: Location to check
            radius: Search radius in meters (default 100m)

        Returns:
            {
                'poi_count': int,
                'commercial_types': list,
                'has_retail': bool,
                'confidence_boost': int (0-25)
            }
        """
        params = {
            'key': self.api_key,
            'location': f'{latitude},{longitude}',
            'radius': radius,
            'type': 'establishment'  # Any commercial establishment
        }

        try:
            response = requests.get(self.places_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'OK':
                return {
                    'poi_count': 0,
                    'commercial_types': [],
                    'has_retail': False,
                    'confidence_boost': 0
                }

            results = data.get('results', [])

            # Filter for commercial types
            commercial_types = set()
            retail_keywords = ['store', 'restaurant', 'cafe', 'shop', 'retail', 'mall']
            has_retail = False

            for place in results:
                types = place.get('types', [])
                commercial_types.update(types)

                # Check if name or types suggest retail
                name = place.get('name', '').lower()
                if any(keyword in name or keyword in ' '.join(types) for keyword in retail_keywords):
                    has_retail = True

            poi_count = len(results)

            # Confidence boost based on commercial activity
            if poi_count >= 5 and has_retail:
                confidence_boost = 25
            elif poi_count >= 3:
                confidence_boost = 15
            elif poi_count >= 1:
                confidence_boost = 5
            else:
                confidence_boost = 0

            return {
                'poi_count': poi_count,
                'commercial_types': list(commercial_types),
                'has_retail': has_retail,
                'confidence_boost': confidence_boost
            }

        except Exception as e:
            print(f"  ⚠️ Places API error: {str(e)}")
            return {
                'poi_count': 0,
                'commercial_types': [],
                'has_retail': False,
                'confidence_boost': 0
            }

    def validate_geocoded_address(self, geocode_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a geocoded address and assign confidence score

        Args:
            geocode_result: Result from GoogleGeocoder.geocode()

        Returns:
            {
                'confidence': int (0-100),
                'has_postal': bool,
                'poi_count': int,
                'validation_notes': str
            }
        """
        if not geocode_result:
            return {
                'confidence': 0,
                'has_postal': False,
                'poi_count': 0,
                'validation_notes': 'Geocoding failed'
            }

        components = geocode_result.get('components', {})
        location = geocode_result.get('location', {})
        postal = components.get('postal_code')

        # Base confidence from geocoding
        base_confidence = geocode_result.get('confidence', 50)

        # Check commercial activity
        lat = location.get('lat')
        lng = location.get('lng')

        if lat and lng:
            poi_data = self.check_commercial_activity(lat, lng)
            poi_count = poi_data['poi_count']
            confidence_boost = poi_data['confidence_boost']
        else:
            poi_count = 0
            confidence_boost = 0

        # Calculate final confidence
        if postal and poi_count >= 3:
            final_confidence = min(100, base_confidence + 25)
            notes = f'Has postal code + {poi_count} commercial POIs nearby'
        elif postal:
            final_confidence = min(100, base_confidence + 10)
            notes = f'Has postal code but no commercial verification'
        elif poi_count >= 3:
            final_confidence = min(75, base_confidence + confidence_boost)
            notes = f'No postal but {poi_count} commercial POIs nearby'
        else:
            final_confidence = max(0, base_confidence - 25)
            notes = f'No postal code and minimal commercial activity'

        return {
            'confidence': final_confidence,
            'has_postal': bool(postal),
            'poi_count': poi_count,
            'validation_notes': notes
        }

    def available(self) -> bool:
        """Check if API key is available"""
        return bool(self.api_key)
