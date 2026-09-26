"""
UC15 GST Compliance Agent — Central Settings
"""
from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.config.defaults import (
    DEFAULT_EXCEL_FILE,
    DEFAULT_SHEET_NAME,
    DEFAULT_RESULTS_DIR,
    SEC_A_HEADER,
    SEC_A_START,
    SEC_A_END,
    SEC_B_HEADER,
    SEC_B_START,
    SEC_B_END,
    SEC_C_HEADER,
    SEC_C_START,
    SEC_C_END,
    SEC_D_HEADER,
    SEC_D_START,
    SEC_D_END,
    DEFAULT_EWAY_BILL_THRESHOLD_INR,
    DEFAULT_ITC_BLOCKED_KEYWORDS,
    DEFAULT_RATE_TOLERANCE_PCT,
    DEFAULT_NEEDS_REVIEW_SLA_HOURS,
    DEFAULT_NON_COMPLIANT_SLA_HOURS,
    DEFAULT_API_PORT,
    DEFAULT_API_HOST,
    DEFAULT_BTP_APP_NAME,
    DEFAULT_BTP_RUNTIME,
    DEFAULT_BTP_MEMORY,
    DEFAULT_ENABLED_RULES,
)

# Load environment variables from .env if present
load_dotenv()


class AppSettings(BaseModel):
    """Centralized application configuration model."""
    app_env: str = Field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    excel_file: str = Field(default_factory=lambda: os.getenv("DATA_PATH", DEFAULT_EXCEL_FILE))
    sheet_name: str = Field(default_factory=lambda: os.getenv("SHEET_NAME", DEFAULT_SHEET_NAME))
    results_dir: str = Field(default_factory=lambda: os.getenv("RESULTS_DIR", DEFAULT_RESULTS_DIR))

    # E-Way Bill threshold
    eway_bill_threshold_inr: Decimal = Field(
        default_factory=lambda: Decimal(os.getenv("EWAY_BILL_THRESHOLD_INR", str(DEFAULT_EWAY_BILL_THRESHOLD_INR)))
    )

    # Tax Rate Tolerance
    rate_tolerance_pct: Decimal = Field(
        default_factory=lambda: Decimal(os.getenv("RATE_TOLERANCE_PCT", str(DEFAULT_RATE_TOLERANCE_PCT)))
    )

    # ITC Blocked Keywords
    itc_blocked_keywords: List[str] = Field(default_factory=lambda: list(DEFAULT_ITC_BLOCKED_KEYWORDS))

    # Turnaround targets (hours)
    needs_review_sla_hours: int = Field(
        default_factory=lambda: int(os.getenv("NEEDS_REVIEW_SLA_HOURS", str(DEFAULT_NEEDS_REVIEW_SLA_HOURS)))
    )
    non_compliant_sla_hours: int = Field(
        default_factory=lambda: int(os.getenv("NON_COMPLIANT_SLA_HOURS", str(DEFAULT_NON_COMPLIANT_SLA_HOURS)))
    )

    # API & Hosting
    api_port: int = Field(
    default_factory=lambda: int(
        os.getenv("PORT", os.getenv("API_PORT", str(DEFAULT_API_PORT)))
    )
)
    api_host: str = Field(default_factory=lambda: os.getenv("API_HOST", DEFAULT_API_HOST))
    btp_app_name: str = DEFAULT_BTP_APP_NAME
    btp_runtime: str = DEFAULT_BTP_RUNTIME
    btp_memory: str = DEFAULT_BTP_MEMORY

    # LLM Settings
    llm_provider: str = Field(default_factory=lambda: os.getenv("LLM_PROVIDER", "openai"))
    llm_model: str = Field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o"))
    llm_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("LLM_API_KEY", None))

    # Rule Configuration
    enabled_rules: List[str] = Field(default_factory=lambda: list(DEFAULT_ENABLED_RULES))

    # SAP S/4HANA Live OData Configuration
    sap_odata_base_url: Optional[str] = Field(default_factory=lambda: os.getenv("SAP_ODATA_BASE_URL", None))
    sap_client: str = Field(default_factory=lambda: os.getenv("SAP_CLIENT", "200"))
    sap_company_code: str = Field(default_factory=lambda: os.getenv("SAP_COMPANY_CODE", "DI01"))
    sap_auth_type: str = Field(default_factory=lambda: os.getenv("SAP_AUTH_TYPE", "basic"))
    sap_username: Optional[str] = Field(default_factory=lambda: os.getenv("SAP_USERNAME", None))
    sap_password: Optional[str] = Field(default_factory=lambda: os.getenv("SAP_PASSWORD", None))
    sap_oauth_token_url: Optional[str] = Field(default_factory=lambda: os.getenv("SAP_OAUTH_TOKEN_URL", None))
    sap_oauth_client_id: Optional[str] = Field(default_factory=lambda: os.getenv("SAP_OAUTH_CLIENT_ID", None))
    sap_oauth_client_secret: Optional[str] = Field(default_factory=lambda: os.getenv("SAP_OAUTH_CLIENT_SECRET", None))
    sap_outward_service: str = Field(default_factory=lambda: os.getenv("SAP_OUTWARD_SERVICE", ""))
    sap_outward_entity: str = Field(default_factory=lambda: os.getenv("SAP_OUTWARD_ENTITY", "OutwardInvoice"))
    sap_inward_service: str = Field(default_factory=lambda: os.getenv("SAP_INWARD_SERVICE", ""))
    sap_inward_entity: str = Field(default_factory=lambda: os.getenv("SAP_INWARD_ENTITY", "InwardInvoice"))



settings = AppSettings()


def get_settings() -> AppSettings:
    """Return application settings singleton."""
    return settings


# -- Backward compatibility constants matching original config/settings.py ----
EXCEL_FILE = settings.excel_file
SHEET_NAME = settings.sheet_name
EWAY_BILL_THRESHOLD_INR = float(settings.eway_bill_threshold_inr)
ITC_BLOCKED_KEYWORDS = settings.itc_blocked_keywords
RATE_TOLERANCE_PCT = float(settings.rate_tolerance_pct)
NEEDS_REVIEW_SLA_HOURS = settings.needs_review_sla_hours
NON_COMPLIANT_SLA_HOURS = settings.non_compliant_sla_hours
BTP_APP_NAME = settings.btp_app_name
BTP_RUNTIME = settings.btp_runtime
BTP_MEMORY = settings.btp_memory
API_PORT = settings.api_port
