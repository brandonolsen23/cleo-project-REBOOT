import os
import time
from typing import Optional, Dict, Any
import requests


class GoogleGeocoder:
    """Google Maps Geocoding API wrapper - same accuracy as Google Maps search"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_GEOCODING_API_KEY")
        self.base_url = "https://maps.googleapis.com/maps/api/geocode/json"

    def available(self) -> bool:
        return bool(self.api_key)

    def geocode(self, address: str, region: str = "CA") -> Optional[Dict[str, Any]]:
        """
        Geocode an address using Google Maps API.
        Returns formatted address, city, postal code, lat/lon, and full components.
        """
        if not self.available():
            return None

        params = {
            "address": address,
            "region": region,
            "key": self.api_key
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]

                # Extract components
                components = {}
                for comp in result.get("address_components", []):
                    types = comp.get("types", [])
                    if "street_number" in types:
                        components["street_number"] = comp["long_name"]
                    if "route" in types:
                        components["street"] = comp["long_name"]
                    if "locality" in types:
                        components["city"] = comp["long_name"]
                    if "administrative_area_level_1" in types:
                        components["province"] = comp["short_name"]
                    if "postal_code" in types:
                        components["postal_code"] = comp["long_name"]

                # Return structured result
                return {
                    "formatted_address": result.get("formatted_address"),
                    "components": components,
                    "location": result.get("geometry", {}).get("location", {}),
                    "place_id": result.get("place_id"),
                    "confidence": "high" if result.get("geometry", {}).get("location_type") == "ROOFTOP" else "medium",
                    "raw": result
                }

            return None

        except Exception as e:
            print(f"Geocoding error: {e}")
            return None
