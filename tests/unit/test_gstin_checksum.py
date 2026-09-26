"""
Unit tests for Indian GSTIN Luhn Modulo-36 Checksum verification (Sprint 2).
"""
import unittest

from app.rules.existing.gstin import (
    GSTINFormatRule,
    calculate_gstin_checksum,
    verify_gstin_checksum,
)
from app.domain.enums.validation_status import ValidationStatus
from app.rules.context import ValidationContext
from tests.fixtures.sample_invoices import make_test_context, make_test_invoice


class TestGSTINChecksum(unittest.TestCase):

    def test_calculate_checksum_for_known_gstin(self):
        # 27AAACB1234A1Z prefix -> expected checksum is 'J'
        prefix = "27AAACB1234A1Z"
        checksum = calculate_gstin_checksum(prefix)
        self.assertEqual(checksum, "J")

        full_valid_gstin = prefix + checksum
        self.assertTrue(verify_gstin_checksum(full_valid_gstin))

    def test_verify_checksum_detects_tampered_character(self):
        # Changed 15th character from 'J' to '5'
        tampered_gstin = "27AAACB1234A1Z5"
        self.assertFalse(verify_gstin_checksum(tampered_gstin))

    def test_calculate_checksum_invalid_lengths(self):
        self.assertIsNone(calculate_gstin_checksum("27SHORT"))
        self.assertIsNone(calculate_gstin_checksum("27AAACB1234A1ZEXTRA"))
        self.assertFalse(verify_gstin_checksum("TOOSHORT"))

    def test_gstin_format_rule_standard_mode_records_evidence(self):
        rule = GSTINFormatRule()
        inv = make_test_invoice(gstin="27AAACB1234A1Z5")  # Valid format, random 15th char
        context = make_test_context()
        context.validate_gstin_checksum = False

        res = rule.validate(inv, context)
        self.assertEqual(res.status, ValidationStatus.PASS.value)
        self.assertIsNotNone(res.evidence)
        self.assertTrue(res.evidence["format_valid"])
        self.assertFalse(res.evidence["checksum_valid"])
        self.assertEqual(res.evidence["expected_checksum"], "J")
        self.assertEqual(res.evidence["actual_checksum"], "5")

    def test_gstin_format_rule_strict_mode_fails_checksum_mismatch(self):
        rule = GSTINFormatRule()
        inv = make_test_invoice(gstin="27AAACB1234A1Z5")
        context = make_test_context()
        context.validate_gstin_checksum = True

        res = rule.validate(inv, context)
        self.assertEqual(res.status, ValidationStatus.FAIL.value)
        self.assertIn("invalid Modulo-36 checksum", res.message)
        self.assertEqual(res.rule_version, "2.0")

    def test_gstin_format_rule_strict_mode_passes_valid_checksum(self):
        rule = GSTINFormatRule()
        inv = make_test_invoice(gstin="27AAACB1234A1ZJ")  # True valid checksum
        context = make_test_context()
        context.validate_gstin_checksum = True

        res = rule.validate(inv, context)
        self.assertEqual(res.status, ValidationStatus.PASS.value)
        self.assertTrue(res.evidence["checksum_valid"])


if __name__ == "__main__":
    unittest.main()
