import os
import time
from typing import Any, Dict, Optional

import requests


class Geocoder:
    def __init__(self, api_key: Optional[str] = None, timeout: int = 15):
        self.api_key = api_key or os.getenv("GEOCODIO_API_KEY")
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key)

    def geocode(self, query: str, country: str = "CA") -> Optional[Dict[str, Any]]:
        if not self.available():
            return None
        base = "https://api.geocod.io/v1.7/geocode"
        params = {
            "q": query,
            "api_key": self.api_key,
            "country": country,
            "limit": 1,
        }
        # simple retry/backoff
        for attempt in range(3):
            try:
                r = requests.get(base, params=params, timeout=self.timeout)
                if r.status_code == 200:
                    data = r.json()
                    results = data.get("results") or []
                    if results:
                        return results[0]
                    return None
                # backoff on 429/5xx
                if r.status_code in (429, 500, 502, 503, 504):
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return None
            except requests.RequestException:
                time.sleep(1.5 * (attempt + 1))
        return None

