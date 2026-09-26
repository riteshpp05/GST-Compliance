"""
Unit tests for multi-source Data Ingestion Layer (Excel, CSV, JSON, Mock) in Sprint 2.
"""
import os
import tempfile
import unittest

from app.data.loaders.csv_loader import CSVInvoiceLoader
from app.data.loaders.excel_loader import ExcelInvoiceLoader
from app.data.loaders.json_loader import JSONInvoiceLoader
from app.data.loaders.mock_loader import MockInvoiceLoader
from app.domain.exceptions import DataLoadError
from app.domain.models.ingestion import IngestionStatus


class TestDataIngestion(unittest.TestCase):

    def test_mock_loader_generates_controlled_scenarios(self):
        loader = MockInvoiceLoader()
        batch = loader.load()

        self.assertGreaterEqual(batch.total_records, 10)
        self.assertGreaterEqual(batch.valid_count, 9)

        summary = batch.summary()
        self.assertIn("success_rate", summary)
        self.assertEqual(summary["source_name"], "MockInvoiceLoader")

    def test_mock_loader_scenario_filter(self):
        loader = MockInvoiceLoader(scenario_filter=["CLEAN_AR", "INVALID_GSTIN_FORMAT", "TAX", "POS"])
        batch = loader.load()
        self.assertGreaterEqual(batch.total_records, 1)

    def test_csv_loader_with_sample_file(self):
        csv_path = os.path.join("data", "raw", "sample_invoices.csv")
        if not os.path.exists(csv_path):
            self.skipTest("Sample CSV file not found")

        loader = CSVInvoiceLoader(csv_path)
        batch = loader.load()

        self.assertEqual(batch.total_records, 6)
        self.assertEqual(batch.valid_count, 6)
        invoices = loader.load_invoices()
        self.assertEqual(len(invoices), 6)
        self.assertEqual(invoices[0].invoice_number, "INV-CSV-001")
        self.assertEqual(invoices[0].source_metadata["source_type"], "csv")

    def test_csv_loader_handles_malformed_and_duplicate_rows(self):
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv") as tmp:
            tmp.write(
                "invoice_no,invoice_date,direction,counterparty_gstin,counterparty_name,place_of_supply,hsn_code,taxable_value_inr,cgst_rate,sgst_rate,igst_rate,total_amt\n"
                "INV-DUP-1,2026-01-01,AR,27AAACB1234A1ZJ,Company A,Maharashtra,8409,10000,9,9,0,11800\n"
                "INV-DUP-1,2026-01-01,AR,27AAACB1234A1ZJ,Company A,Maharashtra,8409,10000,9,9,0,11800\n"  # Duplicate
                ",2026-01-02,AR,27AAACB1234A1ZJ,Company B,Maharashtra,8409,5000,9,9,0,5900\n"  # Missing invoice_no
                "\n"  # Blank row
            )
            tmp_path = tmp.name

        try:
            loader = CSVInvoiceLoader(tmp_path)
            batch = loader.load()
            self.assertEqual(batch.total_records, 3)  # Blank row skipped
            self.assertEqual(batch.valid_count, 1)    # 1 valid, 1 warning (duplicate), 1 invalid (missing ID)
            self.assertEqual(batch.warning_count, 1)
            self.assertEqual(batch.invalid_count, 1)

            # First invoice valid
            self.assertEqual(batch.records[0].status, IngestionStatus.VALID)
            # Second invoice has duplicate warning
            self.assertEqual(batch.records[1].status, IngestionStatus.DATA_QUALITY_WARNING)
            self.assertTrue(any("Duplicate" in w for w in batch.records[1].warnings))
            # Third invoice is incomplete
            self.assertEqual(batch.records[2].status, IngestionStatus.INCOMPLETE)
        finally:
            os.unlink(tmp_path)

    def test_json_loader_with_sample_file(self):
        json_path = os.path.join("data", "raw", "sample_invoices.json")
        if not os.path.exists(json_path):
            self.skipTest("Sample JSON file not found")

        loader = JSONInvoiceLoader(json_path)
        batch = loader.load()

        self.assertEqual(batch.total_records, 3)
        self.assertEqual(batch.valid_count, 3)
        self.assertEqual(batch.valid_invoices[0].invoice_number, "INV-JSON-001")
        self.assertEqual(batch.valid_invoices[0].source_metadata["source_type"], "json")

    def test_json_loader_with_raw_string(self):
        raw_json = '[{"invoice_no": "INV-STR-01", "counterparty_name": "Test", "counterparty_gstin": "27AAACB1234A1ZJ", "place_of_supply": "Maharashtra", "hsn_code": "8409", "taxable_value_inr": 20000}]'
        loader = JSONInvoiceLoader(raw_json, is_content=True)
        batch = loader.load()

        self.assertEqual(batch.total_records, 1)
        self.assertEqual(batch.valid_count, 1)
        self.assertEqual(batch.valid_invoices[0].invoice_number, "INV-STR-01")

    def test_json_loader_handles_malformed_syntax(self):
        bad_json = '{"invoices": [ {"bad_syntax": } ]}'
        loader = JSONInvoiceLoader(bad_json, is_content=True)
        with self.assertRaises(DataLoadError):
            loader.load()

    def test_excel_loader_returns_batch_result(self):
        excel_path = os.path.join("data", "UC15_GSTCompliance_Dataset.xlsx")
        if not os.path.exists(excel_path):
            self.skipTest("Excel dataset not found")

        loader = ExcelInvoiceLoader(excel_path)
        batch = loader.load()

        self.assertGreaterEqual(batch.total_records, 30)
        self.assertGreaterEqual(batch.valid_count, 30)
        self.assertEqual(batch.invalid_count, 0)
        self.assertTrue(batch.valid_invoices[0].source_metadata["source_sheet"], "UC15 - GST Compliance Agent")


if __name__ == "__main__":
    unittest.main()
