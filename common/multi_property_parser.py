"""
Multi-Property Address Parser
Handles patterns like:
- 471 & 481 KING ST E
- 9220 - 9226 HWY 93
- 10, 20 & 30 BROADLEAF AVE
"""
import re
from typing import List, Dict, Any


class MultiPropertyAddressParser:
    """Parse multi-property addresses into individual addresses"""

    # Patterns to detect multi-address formats
    AMPERSAND_PATTERN = r'(\d+)\s*&\s*(\d+)'
    RANGE_DASH_PATTERN = r'(\d+)\s*-\s*(\d+)'
    COMMA_SEPARATED_PATTERN = r'(\d+),\s*(\d+)'

    @staticmethod
    def is_multi_property(address: str) -> bool:
        """Check if address contains multiple property numbers"""
        if not address:
            return False

        has_ampersand = bool(re.search(MultiPropertyAddressParser.AMPERSAND_PATTERN, address))
        has_range = bool(re.search(MultiPropertyAddressParser.RANGE_DASH_PATTERN, address))
        has_comma = bool(re.search(MultiPropertyAddressParser.COMMA_SEPARATED_PATTERN, address))

        return has_ampersand or has_range or has_comma

    @staticmethod
    def parse(address_raw: str, city: str = None) -> Dict[str, Any]:
        """
        Parse a multi-property address into individual addresses

        Returns:
        {
            'is_multi_property': bool,
            'original_address': str,
            'pattern_type': str,  # 'ampersand', 'range_dash', 'comma_separated', or 'single'
            'addresses': [
                {'street_number': str, 'street': str, 'full_address': str, 'position': int},
                ...
            ]
        }
        """
        if not address_raw:
            return {
                'is_multi_property': False,
                'original_address': address_raw,
                'pattern_type': 'single',
                'addresses': []
            }

        # Check for comma separated pattern FIRST (e.g., "10, 20 & 30 BROADLEAF AVE")
        # This must come before ampersand check because comma+ampersand needs special handling
        comma_matches = list(re.finditer(MultiPropertyAddressParser.COMMA_SEPARATED_PATTERN, address_raw))
        if comma_matches:
            return MultiPropertyAddressParser._parse_comma_separated(address_raw, city, comma_matches)

        # Check for range dash pattern (e.g., "9220 - 9226 HWY 93")
        range_matches = list(re.finditer(MultiPropertyAddressParser.RANGE_DASH_PATTERN, address_raw))
        if range_matches:
            return MultiPropertyAddressParser._parse_range_dash(address_raw, city, range_matches)

        # Check for ampersand pattern (e.g., "471 & 481 KING ST E")
        ampersand_matches = list(re.finditer(MultiPropertyAddressParser.AMPERSAND_PATTERN, address_raw))
        if ampersand_matches:
            return MultiPropertyAddressParser._parse_ampersand(address_raw, city, ampersand_matches)

        # Single property
        return {
            'is_multi_property': False,
            'original_address': f"{address_raw}, {city}" if city else address_raw,
            'pattern_type': 'single',
            'addresses': [
                {
                    'street_number': MultiPropertyAddressParser._extract_street_number(address_raw),
                    'street': MultiPropertyAddressParser._extract_street_name(address_raw),
                    'full_address': f"{address_raw}, {city}" if city else address_raw,
                    'position': 1
                }
            ]
        }

    @staticmethod
    def _parse_ampersand(address_raw: str, city: str, matches: List) -> Dict[str, Any]:
        """Parse ampersand pattern: 471 & 481 KING ST E"""
        # Extract all numbers connected by &
        numbers = []
        for match in matches:
            numbers.extend([match.group(1), match.group(2)])

        # Remove duplicates while preserving order
        seen = set()
        unique_numbers = []
        for num in numbers:
            if num not in seen:
                seen.add(num)
                unique_numbers.append(num)

        # Extract street name (everything after the last number pattern)
        # Find the position after the last number pattern
        last_match = matches[-1]
        street_name = address_raw[last_match.end():].strip()

        # Build individual addresses
        addresses = []
        for i, number in enumerate(unique_numbers, 1):
            full_addr = f"{number} {street_name}, {city}" if city else f"{number} {street_name}"
            addresses.append({
                'street_number': number,
                'street': street_name,
                'full_address': full_addr,
                'position': i
            })

        return {
            'is_multi_property': True,
            'original_address': f"{address_raw}, {city}" if city else address_raw,
            'pattern_type': 'ampersand',
            'addresses': addresses
        }

    @staticmethod
    def _parse_range_dash(address_raw: str, city: str, matches: List) -> Dict[str, Any]:
        """Parse range dash pattern: 9220 - 9226 HWY 93 (only start and end)"""
        # Only take first and last number from the range
        match = matches[0]  # Should only be one range match
        start_num = match.group(1)
        end_num = match.group(2)

        # Extract street name (everything after the range)
        street_name = address_raw[match.end():].strip()

        # Build addresses for start and end only
        addresses = []
        for i, number in enumerate([start_num, end_num], 1):
            full_addr = f"{number} {street_name}, {city}" if city else f"{number} {street_name}"
            addresses.append({
                'street_number': number,
                'street': street_name,
                'full_address': full_addr,
                'position': i
            })

        return {
            'is_multi_property': True,
            'original_address': f"{address_raw}, {city}" if city else address_raw,
            'pattern_type': 'range_dash',
            'addresses': addresses
        }

    @staticmethod
    def _parse_comma_separated(address_raw: str, city: str, matches: List) -> Dict[str, Any]:
        """Parse comma separated pattern: 10, 20 & 30 BROADLEAF AVE"""
        # This handles mixed comma and ampersand (e.g., "10, 20 & 30 BROADLEAF AVE")
        # Extract ALL numbers at the beginning, separated by commas or ampersands

        # Find all numbers followed by comma, ampersand, or space before street name
        all_numbers = []

        # Pattern to find all numbers with separators
        number_with_separator = r'(\d+)\s*(?:,|&)'
        for match in re.finditer(number_with_separator, address_raw):
            all_numbers.append(match.group(1))

        # Find the last number (followed by a space and capital letter - start of street name)
        last_number_match = re.search(r'(?:,|&)\s*(\d+)\s+([A-Z])', address_raw)
        if last_number_match:
            all_numbers.append(last_number_match.group(1))
            street_name = address_raw[last_number_match.end()-1:].strip()
        else:
            # No last number found with street pattern, extract street after all numbers/separators
            # Remove all numbers and their separators from the beginning
            street_name = re.sub(r'^[\d\s,&]+', '', address_raw).strip()

        # Build individual addresses
        addresses = []
        for i, number in enumerate(all_numbers, 1):
            full_addr = f"{number} {street_name}, {city}" if city else f"{number} {street_name}"
            addresses.append({
                'street_number': number,
                'street': street_name,
                'full_address': full_addr,
                'position': i
            })

        return {
            'is_multi_property': True,
            'original_address': f"{address_raw}, {city}" if city else address_raw,
            'pattern_type': 'comma_separated',
            'addresses': addresses
        }

    @staticmethod
    def _extract_street_number(address: str) -> str:
        """Extract street number from address"""
        match = re.match(r'^(\d+)', address.strip())
        return match.group(1) if match else None

    @staticmethod
    def _extract_street_name(address: str) -> str:
        """Extract street name from address (everything after first number)"""
        match = re.match(r'^\d+\s+(.+)', address.strip())
        return match.group(1) if match else address
