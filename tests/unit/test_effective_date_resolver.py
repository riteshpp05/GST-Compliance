"""
UC15 GST Compliance Agent — Unit Tests: Effective Date Resolver (Sprint 4)
Exhaustive test suite verifying temporal boundary conditions, conflicts, and resolutions.
"""
import unittest
from datetime import date

from app.reference.models.base import BaseReferenceRecord
from app.reference.resolvers.effective_date import (
    EffectiveDateResolver,
    ResolutionStatus,
)


class TestEffectiveDateResolver(unittest.TestCase):
    """Temporal resolution test matrix covering all boundary conditions."""

    def setUp(self):
        self.v1 = BaseReferenceRecord(
            reference_id="REF_V1",
            reference_type="TAX_RATE",
            version="1.0",
            effective_from=date(2018, 1, 1),
            effective_to=date(2020, 12, 31),
            status="ACTIVE",
        )
        self.v2 = BaseReferenceRecord(
            reference_id="REF_V2",
            reference_type="TAX_RATE",
            version="2.0",
            effective_from=date(2021, 1, 1),
            effective_to=None,  # Open-ended
            status="ACTIVE",
        )

    def test_before_effective_window_not_found(self):
        """Transaction date before any version became active returns NOT_FOUND."""
        res = EffectiveDateResolver.resolve([self.v1, self.v2], date(2017, 12, 31))
        self.assertEqual(res.status, ResolutionStatus.NOT_FOUND)
        self.assertTrue(res.is_not_found)
        self.assertIsNone(res.reference)
        self.assertIn("No active", res.reason)

    def test_exactly_on_effective_from_resolved(self):
        """Target date on the exact starting date returns RESOLVED."""
        res = EffectiveDateResolver.resolve([self.v1, self.v2], date(2018, 1, 1))
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertTrue(res.is_resolved)
        self.assertEqual(res.reference_id, "REF_V1")
        self.assertEqual(res.reference_version, "1.0")

    def test_strictly_inside_window_resolved(self):
        """Target date strictly inside effective window returns RESOLVED."""
        res = EffectiveDateResolver.resolve([self.v1, self.v2], date(2019, 6, 15))
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.reference_id, "REF_V1")

    def test_exactly_on_effective_to_resolved(self):
        """Target date on the exact closing date returns RESOLVED."""
        res = EffectiveDateResolver.resolve([self.v1, self.v2], date(2020, 12, 31))
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.reference_id, "REF_V1")

    def test_transition_to_v2_resolved(self):
        """Target date immediately on next day resolves to v2."""
        res = EffectiveDateResolver.resolve([self.v1, self.v2], date(2021, 1, 1))
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.reference_id, "REF_V2")
        self.assertEqual(res.reference_version, "2.0")

    def test_open_ended_future_resolved(self):
        """Open-ended reference resolves far into the future."""
        res = EffectiveDateResolver.resolve([self.v1, self.v2], date(2028, 10, 5))
        self.assertEqual(res.status, ResolutionStatus.RESOLVED)
        self.assertEqual(res.reference_id, "REF_V2")

    def test_conflict_on_overlapping_effective_windows(self):
        """Overlapping active references on target date return CONFLICT."""
        overlap_a = BaseReferenceRecord(
            reference_id="OVERLAP_A",
            reference_type="TAX_RATE",
            version="1.0",
            effective_from=date(2022, 1, 1),
            effective_to=date(2023, 12, 31),
            status="ACTIVE",
        )
        overlap_b = BaseReferenceRecord(
            reference_id="OVERLAP_B",
            reference_type="TAX_RATE",
            version="2.0",
            effective_from=date(2022, 6, 1),
            effective_to=date(2024, 6, 1),
            status="ACTIVE",
        )

        res = EffectiveDateResolver.resolve([overlap_a, overlap_b], date(2023, 1, 1))
        self.assertEqual(res.status, ResolutionStatus.CONFLICT)
        self.assertTrue(res.is_conflict)
        self.assertFalse(res.is_resolved)
        self.assertIsNone(res.reference)
        self.assertIn("conflict", res.reason.lower())
        self.assertEqual(len(res.candidates), 2)

    def test_inactive_status_ignored(self):
        """Inactive / superseded records are ignored during active window resolution."""
        inactive_rec = BaseReferenceRecord(
            reference_id="INACTIVE_REF",
            reference_type="TAX_RATE",
            version="1.0",
            effective_from=date(2020, 1, 1),
            effective_to=date(2025, 1, 1),
            status="INACTIVE",  # Disabled
        )
        res = EffectiveDateResolver.resolve([inactive_rec], date(2022, 1, 1))
        self.assertEqual(res.status, ResolutionStatus.NOT_FOUND)

    def test_invalid_reference_inverted_dates(self):
        """Candidate with inverted effective date range returns INVALID_REFERENCE."""
        invalid_rec = BaseReferenceRecord(
            reference_id="INVALID_RANGE",
            reference_type="TAX_RATE",
            version="1.0",
            effective_from=date(2025, 1, 1),
            effective_to=date(2020, 1, 1),
            status="ACTIVE",
        )
        res = EffectiveDateResolver.resolve([invalid_rec], date(2022, 1, 1))
        self.assertEqual(res.status, ResolutionStatus.INVALID_REFERENCE)
        self.assertIn("invalid date window", res.reason.lower())


if __name__ == "__main__":
    unittest.main()
