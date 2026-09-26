"""
tests.unit.test_s17_ingestion
=============================
Sprint 17 Unit Test Suite: Data Sources, Schema Validation, Normalization, & Deduplication.
"""

import unittest
from app.data.deduplication import DeduplicationEngine, DuplicateStatus
from app.data.normalization.invoice_normalizer import InvoiceNormalizer
from app.data.sources import CSVDataSource, DictListDataSource, ERPExportDataSource, JSONDataSource
from app.data.validation import SchemaValidator
from app.domain.models.ingestion import SourceMetadata


class TestS17DataSources(unittest.TestCase):
    """Test suite for Data Source abstractions and concrete adapters."""

    def test_csv_data_source_parsing(self):
        csv_data = "invoice_number,supplier_gstin,invoice_date,taxable_value\nINV-9001,27ABCDE1234F1Z5,2026-04-01,10000.00"
        src = CSVDataSource(source_id="SRC-CSV-01", source_name="Test CSV", csv_content=csv_data)
        self.assertTrue(src.connect())
        records = src.fetch_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["invoice_number"], "INV-9001")

    def test_json_data_source_parsing(self):
        json_data = [{"invoice_number": "INV-9002", "supplier_gstin": "29XCDBM5846M9ZE", "invoice_date": "2026-04-02", "taxable_value": 15000.0}]
        src = JSONDataSource(source_id="SRC-JSON-01", source_name="Test JSON", json_content=json_data)
        self.assertTrue(src.connect())
        records = src.fetch_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["invoice_number"], "INV-9002")

    def test_erp_export_adapter(self):
        # File export adapter only, no live SAP
        erp_csv = "inv_num,seller_gstin,date,base_amount\nSAP-INV-001,33LULIS8382M2ZV,2026-04-03,50000.00"
        src = ERPExportDataSource(source_id="SRC-ERP-01", source_name="SAP Export", raw_export_data=erp_csv)
        self.assertTrue(src.connect())
        records = src.fetch_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["inv_num"], "SAP-INV-001")


class TestS17SchemaValidation(unittest.TestCase):
    """Test suite for structural schema validation."""

    def test_valid_structure_passes(self):
        rec = {"invoice_number": "INV-100", "supplier_gstin": "27ABCDE1234F1Z5", "taxable_value": "1000.00", "invoice_date": "2026-04-01"}
        res = SchemaValidator.validate_structure(rec)
        self.assertTrue(res.is_valid)
        self.assertEqual(len(res.errors), 0)

    def test_missing_required_field_fails(self):
        rec = {"taxable_value": "1000.00"}
        res = SchemaValidator.validate_structure(rec)
        self.assertFalse(res.is_valid)
        self.assertGreater(len(res.errors), 0)

    def test_malformed_numeric_fails(self):
        rec = {"invoice_number": "INV-100", "supplier_gstin": "27ABCDE1234F1Z5", "taxable_value": "INVALID_NUM"}
        res = SchemaValidator.validate_structure(rec)
        self.assertFalse(res.is_valid)
        self.assertIn("taxable_value", res.malformed_fields)


class TestS17NormalizationAndDeduplication(unittest.TestCase):
    """Test suite for normalization idempotency and deduplication signals."""

    def test_normalization_clean_gstin_and_date(self):
        self.assertEqual(InvoiceNormalizer.clean_gstin(" 27abcde1234f1z5 "), "27ABCDE1234F1Z5")
        self.assertEqual(InvoiceNormalizer.clean_date("01/04/2026"), "2026-04-01")

    def test_normalization_idempotency(self):
        raw = {"invoice_number": " INV-200 ", "gstin": " 27abcde1234f1z5 ", "invoice_date": "01/04/2026", "taxable_value": "10,000.00"}
        meta = SourceMetadata(source_name="Unit Test")
        res1 = InvoiceNormalizer.normalize_record(raw, source_metadata=meta)
        self.assertTrue(res1.is_valid)
        inv1 = res1.invoice

        # Second normalization pass must yield identical canonical representation
        res2 = InvoiceNormalizer.normalize_record(inv1.model_dump(), source_metadata=meta)
        self.assertTrue(res2.is_valid)
        inv2 = res2.invoice

        self.assertEqual(inv1.gstin, inv2.gstin)
        self.assertEqual(inv1.invoice_date, inv2.invoice_date)
        self.assertEqual(inv1.taxable_value, inv2.taxable_value)

    def test_exact_and_potential_duplicates(self):
        # Exact duplicate check
        fp1 = DeduplicationEngine.compute_exact_fingerprint("27ABCDE1234F1Z5", "INV-300", "2026-04-01", 10000.0)
        fp2 = DeduplicationEngine.compute_exact_fingerprint("27ABCDE1234F1Z5", "INV-300", "2026-04-01", 10000.0)
        self.assertEqual(fp1, fp2)

        res_exact = DeduplicationEngine.evaluate_record(
            supplier_gstin="27ABCDE1234F1Z5",
            invoice_number="INV-300",
            invoice_date="2026-04-01",
            taxable_value=10000.0,
            existing_exact_fps={fp1: "CANON-INV-300"},
        )
        self.assertEqual(res_exact.status, DuplicateStatus.EXACT_DUPLICATE)
        self.assertEqual(res_exact.matched_record_id, "CANON-INV-300")

        # Potential duplicate check (different amount)
        p_fp = DeduplicationEngine.compute_potential_fingerprint("27ABCDE1234F1Z5", "INV-300", "2026-04-01")
        res_potential = DeduplicationEngine.evaluate_record(
            supplier_gstin="27ABCDE1234F1Z5",
            invoice_number="INV-300",
            invoice_date="2026-04-01",
            taxable_value=12000.0,  # Different amount
            existing_potential_fps={p_fp: "CANON-INV-300"},
        )
        # MUST BE POTENTIAL_DUPLICATE review signal, NOT hard deletion or rejection
        self.assertEqual(res_potential.status, DuplicateStatus.POTENTIAL_DUPLICATE)
        self.assertEqual(res_potential.matched_record_id, "CANON-INV-300")
