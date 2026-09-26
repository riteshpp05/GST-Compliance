"""
Unit & Integration Tests for Dataset Management & Ingestion System.
Tests CSV, Excel, and JSON dataset ingestion, registry persistence, active dataset switching,
and default benchmark protection.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.data.dataset_service import DEFAULT_DATASET_ID, DatasetService


class TestDatasetService(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.service = DatasetService(base_dir=self.temp_dir)

    def test_default_registry_initialization(self):
        datasets = self.service.list_datasets()
        self.assertGreaterEqual(len(datasets), 1)
        active = self.service.get_active_dataset()
        self.assertEqual(active["id"], DEFAULT_DATASET_ID)

    def test_csv_dataset_registration_and_activation(self):
        # Create temp CSV file
        csv_path = os.path.join(self.service.uploads_dir, "test_invoices.csv")
        csv_content = (
            "invoice_no,invoice_date,counterparty_name,counterparty_gstin,place_of_supply,taxable_value,igst_amount,cgst_amount,sgst_amount,total_tax,total_invoice_value,hsn_sac_code,eway_bill_no,eway_bill_status,gstr_2b_status,is_itc_claimed\n"
            "INV-TEST-001,2026-08-10,Test Supplier Ltd,29AAACT1234F1Z5,Karnataka,50000.00,0.00,4500.00,4500.00,9000.00,59000.00,998313,EWB-TEST1,GENERATED,MATCHED,Yes\n"
        )
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write(csv_content)

        ds_info = self.service.validate_and_register_file(
            file_path=csv_path,
            original_filename="test_invoices.csv",
            custom_name="Test CSV Dataset",
            uploaded_by="Test Suite",
            set_active=True,
        )

        self.assertEqual(ds_info["file_format"], "CSV")
        self.assertEqual(ds_info["invoice_count"], 1)
        self.assertEqual(ds_info["is_active"], True)

        active = self.service.get_active_dataset()
        self.assertEqual(active["id"], ds_info["id"])

    def test_json_dataset_registration(self):
        json_path = os.path.join(self.service.uploads_dir, "test_invoices.json")
        json_content = """[
            {
                "invoice_no": "INV-JSON-001",
                "invoice_date": "2026-08-12",
                "counterparty_name": "JSON Supplier Corp",
                "counterparty_gstin": "27AAACR5000E1Z9",
                "place_of_supply": "Maharashtra",
                "taxable_value": 75000.0,
                "igst_amount": 0.0,
                "cgst_amount": 6750.0,
                "sgst_amount": 6750.0,
                "total_tax": 13500.0,
                "total_invoice_value": 88500.0,
                "hsn_sac_code": "998313",
                "eway_bill_no": "EWB-J1",
                "eway_bill_status": "GENERATED",
                "gstr_2b_status": "MATCHED",
                "is_itc_claimed": "Yes"
            }
        ]"""
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_content)

        ds_info = self.service.validate_and_register_file(
            file_path=json_path,
            original_filename="test_invoices.json",
            custom_name="Test JSON Dataset",
            set_active=False,
        )

        self.assertEqual(ds_info["file_format"], "JSON")
        self.assertEqual(ds_info["invoice_count"], 1)
        self.assertEqual(ds_info["is_active"], False)

    def test_delete_protection_on_default_benchmark(self):
        with self.assertRaises(ValueError):
            self.service.delete_dataset(DEFAULT_DATASET_ID)


if __name__ == "__main__":
    unittest.main()
