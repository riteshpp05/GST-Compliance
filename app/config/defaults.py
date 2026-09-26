"""
UC15 GST Compliance Agent — Default Configurations & Constants
"""
from __future__ import annotations
from decimal import Decimal

# Dataset and Sheet Configuration
DEFAULT_EXCEL_FILE = "data/UC15_GSTCompliance_Dataset.xlsx"
DEFAULT_SHEET_NAME = "UC15 - GST Compliance Agent"
DEFAULT_RESULTS_DIR = "results"

# Excel Row Bounds (Section-based layout)
SEC_A_HEADER = 4
SEC_A_START = 5
SEC_A_END = 104     # AR/AP Invoices (100 rows)

SEC_B_HEADER = 36
SEC_B_START = 37
SEC_B_END = 51      # HSN/SAC Master with correct rates (15 rows)

SEC_C_HEADER = 53
SEC_C_START = 54
SEC_C_END = 63      # GSTIN State Code Reference (10 rows)

SEC_D_HEADER = 65
SEC_D_START = 66
SEC_D_END = 95      # Agent Output Reference (30 rows)

# E-Way Bill Thresholds
DEFAULT_EWAY_BILL_THRESHOLD_INR = Decimal("50000")

# Input Tax Credit (ITC) Blocked Keywords under Section 17(5)
DEFAULT_ITC_BLOCKED_KEYWORDS = [
    "employee welfare",
    "food and beverage",
    "outdoor catering",
    "rent-a-cab",
    "club membership",
    "health insurance - employee",
    "personal use",
]

# Tax Rate Tolerance
DEFAULT_RATE_TOLERANCE_PCT = Decimal("0.01")

# Service Level Agreements (Turnaround in hours)
DEFAULT_NEEDS_REVIEW_SLA_HOURS = 24
DEFAULT_NON_COMPLIANT_SLA_HOURS = 4

# API & Server Defaults
DEFAULT_API_PORT = 8000
DEFAULT_API_HOST = "0.0.0.0"

# BTP Deployment Defaults
DEFAULT_BTP_APP_NAME = "uc15-gst-compliance-agent"
DEFAULT_BTP_RUNTIME = "python_buildpack"
DEFAULT_BTP_MEMORY = "512M"

# Initial Feature Flags & Business Rules Configuration
DEFAULT_ENABLED_RULES = [
    "GSTIN_001",
    "HSN_001",
    "TAX_001",
    "POS_001",
    "EWB_001",
    "ITC_001",
]
