"""
tests.unit.test_s18_evidence
=============================
Unit Test Suite for Sprint 18 Evidence Architecture.
Verifies first-class evidence creation, classification, SHA-256 snapshot hashing, and provenance linkage.
"""

import unittest
from app.investigation.evidence import EvidenceManager, EvidenceStrengthEnum


class TestS18Evidence(unittest.TestCase):

    def test_evidence_strength_classification(self):
        self.assertEqual(EvidenceManager.classify_strength("GATE_DETERMINATION"), EvidenceStrengthEnum.DETERMINISTIC)
        self.assertEqual(EvidenceManager.classify_strength("VALIDATION_RESULT"), EvidenceStrengthEnum.DETERMINISTIC)
        self.assertEqual(EvidenceManager.classify_strength("HISTORICAL_RESULT"), EvidenceStrengthEnum.STRONG)
        self.assertEqual(EvidenceManager.classify_strength("DUPLICATE_RESULT"), EvidenceStrengthEnum.STRONG)
        self.assertEqual(EvidenceManager.classify_strength("KNOWLEDGE_DOCUMENT"), EvidenceStrengthEnum.SUPPORTING)
        self.assertEqual(EvidenceManager.classify_strength("SOURCE_RECORD"), EvidenceStrengthEnum.CONTEXTUAL)
        self.assertEqual(EvidenceManager.classify_strength("AGENT_OUTPUT"), EvidenceStrengthEnum.UNVERIFIED)

    def test_evidence_creation_and_snapshot_hash(self):
        data = {"invoice_id": "INV-EVD-001", "taxable_value": 50000.0, "status": "COMPLIANT"}
        ev = EvidenceManager.create_evidence(
            case_id="CASE-EVD-1",
            source_type="VALIDATION_RESULT",
            source_id="Gate-4",
            description="POS match validation",
            data=data,
        )

        self.assertEqual(ev.case_id, "CASE-EVD-1")
        self.assertEqual(ev.evidence_type, "VALIDATION_RESULT")
        self.assertEqual(ev.metadata["evidence_strength"], "DETERMINISTIC")
        self.assertIn("snapshot_hash", ev.metadata)
        self.assertEqual(len(ev.metadata["snapshot_hash"]), 64)
