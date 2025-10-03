"""
Unit tests for address parser
"""

import unittest

from common.address_parser import (
    build_canonical_address,
    extract_unit_number,
    parse_and_validate_city,
    parse_canadian_address,
)
from common.ontario_cities import (
    extract_city_from_canonical,
    is_likely_unit_or_address,
    is_valid_city,
    normalize_city,
)


class TestOntarioCities(unittest.TestCase):
    """Test Ontario city validation and normalization."""

    def test_valid_cities(self):
        """Test that major cities are recognized."""
        self.assertTrue(is_valid_city("Toronto"))
        self.assertTrue(is_valid_city("TORONTO"))
        self.assertTrue(is_valid_city("toronto"))
        self.assertTrue(is_valid_city("Brampton"))
        self.assertTrue(is_valid_city("Hamilton"))
        self.assertTrue(is_valid_city("Ottawa"))

    def test_invalid_cities(self):
        """Test that non-cities are rejected."""
        self.assertFalse(is_valid_city("Unit 1"))
        self.assertFalse(is_valid_city("Suite 105"))
        self.assertFalse(is_valid_city("123 Main St"))
        self.assertFalse(is_valid_city(""))
        self.assertFalse(is_valid_city(None))

    def test_amalgamated_cities(self):
        """Test that old municipality names are mapped to current cities."""
        self.assertEqual(normalize_city("Scarborough"), "TORONTO")
        self.assertEqual(normalize_city("Etobicoke"), "TORONTO")
        self.assertEqual(normalize_city("North York"), "TORONTO")
        self.assertEqual(normalize_city("Ancaster"), "HAMILTON")
        self.assertEqual(normalize_city("Dundas"), "HAMILTON")

    def test_sub_municipality_suffix_removal(self):
        """Test that sub-municipality suffixes are removed."""
        self.assertEqual(normalize_city("Toronto (Scarborough)"), "TORONTO")
        self.assertEqual(normalize_city("Hamilton (Ancaster)"), "HAMILTON")
        self.assertEqual(normalize_city("Halton Hills (Georgetown)"), "HALTON HILLS")

    def test_is_likely_unit_or_address(self):
        """Test detection of unit numbers and addresses in city field."""
        # Unit indicators
        self.assertTrue(is_likely_unit_or_address("Unit 1"))
        self.assertTrue(is_likely_unit_or_address("Suite 105"))
        self.assertTrue(is_likely_unit_or_address("Apt 24"))
        self.assertTrue(is_likely_unit_or_address("Unit #24"))
        self.assertTrue(is_likely_unit_or_address("#42"))

        # Address indicators
        self.assertTrue(is_likely_unit_or_address("123 Main Street"))
        self.assertTrue(is_likely_unit_or_address("5800 MAVIS RD"))
        self.assertTrue(is_likely_unit_or_address("345 King Street West"))

        # Valid cities
        self.assertFalse(is_likely_unit_or_address("Toronto"))
        self.assertFalse(is_likely_unit_or_address("Brampton"))

    def test_extract_city_from_canonical(self):
        """Test extracting city from canonical address strings."""
        # Standard format
        self.assertEqual(
            extract_city_from_canonical("9025 AIRPORT ROAD, BRAMPTON, ON, CA"),
            "BRAMPTON"
        )

        # With unit number
        self.assertEqual(
            extract_city_from_canonical("9025 AIRPORT ROAD, UNIT 1, BRAMPTON, ON, CA"),
            "BRAMPTON"
        )

        # Without province
        self.assertEqual(
            extract_city_from_canonical("123 MAIN ST, TORONTO, CA"),
            "TORONTO"
        )

        # Invalid format
        self.assertIsNone(extract_city_from_canonical("123 Main St"))
        self.assertIsNone(extract_city_from_canonical(""))
        self.assertIsNone(extract_city_from_canonical(None))


class TestUnitExtraction(unittest.TestCase):
    """Test unit number extraction from addresses."""

    def test_extract_unit_patterns(self):
        """Test various unit number patterns."""
        # Unit
        addr, unit = extract_unit_number("123 Main St Unit 5")
        self.assertEqual(addr, "123 Main St")
        self.assertEqual(unit, "5")

        # Suite
        addr, unit = extract_unit_number("123 Main St Suite 105")
        self.assertEqual(addr, "123 Main St")
        self.assertEqual(unit, "105")

        # Apt
        addr, unit = extract_unit_number("123 Main St Apt. 24")
        self.assertEqual(addr, "123 Main St")
        self.assertEqual(unit, "24")

        # Hash prefix
        addr, unit = extract_unit_number("123 Main St #42")
        self.assertEqual(addr, "123 Main St")
        self.assertEqual(unit, "42")

        # Unit with letter suffix
        addr, unit = extract_unit_number("123 Main St Unit 5A")
        self.assertEqual(addr, "123 Main St")
        self.assertEqual(unit, "5A")

    def test_no_unit(self):
        """Test addresses without unit numbers."""
        addr, unit = extract_unit_number("123 Main St")
        self.assertEqual(addr, "123 Main St")
        self.assertIsNone(unit)


class TestParseAndValidateCity(unittest.TestCase):
    """Test city parsing and validation logic."""

    def test_valid_city_raw(self):
        """Test that valid cities are returned normalized."""
        city = parse_and_validate_city(
            address="123 Main St",
            city_raw="Toronto",
            province="ON"
        )
        self.assertEqual(city, "TORONTO")

        city = parse_and_validate_city(
            address="123 Main St",
            city_raw="brampton",
            province="ON"
        )
        self.assertEqual(city, "BRAMPTON")

    def test_unit_in_city_field_with_canonical(self):
        """Test that unit numbers in city field trigger canonical extraction."""
        city = parse_and_validate_city(
            address="9025 Airport Road",
            city_raw="Unit 1",
            province="ON",
            canonical="9025 AIRPORT ROAD, UNIT 1, BRAMPTON, ON, CA"
        )
        self.assertEqual(city, "BRAMPTON")

    def test_unit_in_city_field_without_canonical(self):
        """Test that unit numbers in city field without canonical returns None."""
        city = parse_and_validate_city(
            address="9025 Airport Road",
            city_raw="Unit 1",
            province="ON"
        )
        self.assertIsNone(city)

    def test_amalgamated_city(self):
        """Test that amalgamated cities are normalized."""
        city = parse_and_validate_city(
            address="123 Main St",
            city_raw="Scarborough",
            province="ON"
        )
        self.assertEqual(city, "TORONTO")

    def test_sub_municipality_suffix(self):
        """Test that sub-municipality suffixes are removed."""
        city = parse_and_validate_city(
            address="123 Main St",
            city_raw="Toronto (Scarborough)",
            province="ON"
        )
        self.assertEqual(city, "TORONTO")


class TestParseCanadianAddress(unittest.TestCase):
    """Test full address parsing."""

    def test_parse_clean_address(self):
        """Test parsing a clean address."""
        result = parse_canadian_address(
            address="123 Main Street",
            city="Toronto",
            province="ON"
        )
        self.assertEqual(result.street_address, "123 Main Street")
        self.assertEqual(result.city, "TORONTO")
        self.assertEqual(result.province, "ON")
        self.assertIsNone(result.unit_number)

    def test_parse_address_with_unit(self):
        """Test parsing address with embedded unit number."""
        result = parse_canadian_address(
            address="123 Main Street Unit 5",
            city="Toronto",
            province="ON"
        )
        self.assertEqual(result.street_address, "123 Main Street")
        self.assertEqual(result.city, "TORONTO")
        self.assertEqual(result.unit_number, "5")

    def test_parse_with_unit_in_city_field(self):
        """Test parsing when unit is in city field."""
        result = parse_canadian_address(
            address="9025 Airport Road",
            city="Unit 1",
            province="ON",
            canonical="9025 AIRPORT ROAD, UNIT 1, BRAMPTON, ON, CA"
        )
        self.assertEqual(result.street_address, "9025 Airport Road")
        self.assertEqual(result.city, "BRAMPTON")
        self.assertIsNone(result.unit_number)  # Unit is in city field, not address

    def test_parse_with_invalid_city(self):
        """Test parsing with invalid city and no canonical."""
        result = parse_canadian_address(
            address="123 Main St",
            city="InvalidCity123",
            province="ON"
        )
        self.assertEqual(result.street_address, "123 Main St")
        self.assertIsNone(result.city)
        self.assertTrue(len(result.warnings) > 0)


class TestBuildCanonical(unittest.TestCase):
    """Test canonical address building."""

    def test_build_standard_canonical(self):
        """Test building standard canonical address."""
        canonical = build_canonical_address(
            address="123 Main Street",
            city="Toronto",
            province="ON",
            country="CA"
        )
        self.assertEqual(canonical, "123 MAIN STREET, TORONTO, ON, CA")

    def test_build_with_missing_parts(self):
        """Test building canonical with missing components."""
        canonical = build_canonical_address(
            address="123 Main Street",
            city="Toronto",
            province="",
            country="CA"
        )
        self.assertEqual(canonical, "123 MAIN STREET, TORONTO, CA")


if __name__ == "__main__":
    unittest.main()
