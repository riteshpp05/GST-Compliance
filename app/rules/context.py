"""
UC15 GST Compliance Agent — Rule Validation Context (Sprint 4)
Provides externalized master references, temporal reference service, and runtime configuration.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.config.settings import settings
from app.domain.models.tax import HSNMaster
from app.reference.models.hsn import HSNReference
from app.reference.models.snapshot import ReferenceSnapshot
from app.reference.models.state import StateReference
from app.reference.models.tax_rate import TaxRateReference
from app.reference.services.reference_service import ReferenceService


class ValidationContext(BaseModel):
    """Contextual master data, policy thresholds, and runtime flags passed to compliance rules."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    hsn_master: Dict[str, HSNMaster] = Field(default_factory=dict)
    state_ref: Dict[str, str] = Field(default_factory=dict)
    eway_bill_threshold: Decimal = Field(default_factory=lambda: settings.eway_bill_threshold_inr)
    rate_tolerance_pct: Decimal = Field(default_factory=lambda: settings.rate_tolerance_pct)
    itc_blocked_keywords: List[str] = Field(default_factory=lambda: list(settings.itc_blocked_keywords))
    transaction_context: Optional[Any] = None
    
    # Strict GSTIN Luhn Modulo-36 Checksum verification
    validate_gstin_checksum: bool = False
    
    # Sprint 4: Reference Service & Snapshots
    reference_service: Any = Field(default_factory=ReferenceService)
    current_snapshot: Optional[ReferenceSnapshot] = None
    
    runtime_metadata: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        if self.reference_service is None:
            self.reference_service = ReferenceService()
        self._adapt_legacy_inputs()

    def _adapt_legacy_inputs(self) -> None:
        """Adapt legacy hsn_master and state_ref inputs into ReferenceService repository without overriding statutory data."""
        if not self.reference_service or not hasattr(self.reference_service, "repository"):
            return
        repo = self.reference_service.repository

        for code, hsn_item in self.hsn_master.items():
            clean_code = str(code).strip()
            # FIX 5: Eliminate silent competing sources of truth.
            # Official statutory records in the reference repository take precedence.
            existing_candidates = repo.get_hsn_candidates(clean_code)
            if any(getattr(c, "source", None) == "OFFICIAL_GST" for c in existing_candidates):
                continue

            desc = getattr(hsn_item, "description", "")
            cgst = Decimal(str(getattr(hsn_item, "correct_cgst_rate", 0)))
            sgst = Decimal(str(getattr(hsn_item, "correct_sgst_rate", 0)))
            igst = Decimal(str(getattr(hsn_item, "correct_igst_rate", 0)))

            hsn_rec = HSNReference(
                reference_id=f"LEGACY_HSN_{clean_code}",
                version="1.0-legacy",
                effective_from=date(2017, 7, 1),
                code=clean_code,
                description=desc,
                default_cgst_rate=cgst,
                default_sgst_rate=sgst,
                default_igst_rate=igst,
                source="LEGACY_ADAPTED",
            )
            tax_rec = TaxRateReference(
                reference_id=f"LEGACY_TAX_{clean_code}",
                version="1.0-legacy",
                effective_from=date(2017, 7, 1),
                hsn_code=clean_code,
                cgst_rate=cgst,
                sgst_rate=sgst,
                igst_rate=igst,
                description=desc,
                source="LEGACY_ADAPTED",
            )
            if hasattr(repo, "add_legacy_hsn"):
                repo.add_legacy_hsn(hsn_rec)
                repo.add_legacy_tax_rate(tax_rec)
            else:
                repo.add_hsn(hsn_rec)
                repo.add_tax_rate(tax_rec)

        for code, name in self.state_ref.items():
            clean_code = str(code).strip().zfill(2)
            existing_states = repo.get_state_candidates(clean_code)
            if any(getattr(c, "source", None) == "OFFICIAL_GST" for c in existing_states):
                continue

            st_rec = StateReference(
                reference_id=f"LEGACY_STATE_{clean_code}",
                version="1.0-legacy",
                effective_from=date(2017, 7, 1),
                state_code=clean_code,
                state_name=name,
                source="LEGACY_ADAPTED",
            )
            if hasattr(repo, "add_legacy_state"):
                repo.add_legacy_state(st_rec)
            else:
                repo.add_state(st_rec)

        if hasattr(self.reference_service, "clear_cache"):
            self.reference_service.clear_cache()

    def get_hsn(self, hsn_code: str, target_date: Optional[date] = None) -> Optional[HSNMaster]:
        """Look up HSN classification resolved from reference service (single source of truth)."""
        if self.reference_service:
            d = target_date or date(2023, 1, 1)
            res = self.reference_service.resolve_hsn(hsn_code, d)
            if res.is_resolved:
                rec = res.record
                return HSNMaster(
                    hsn_code=rec.code,
                    description=rec.description,
                    correct_cgst_rate=rec.default_cgst_rate or Decimal("0.0"),
                    correct_sgst_rate=rec.default_sgst_rate or Decimal("0.0"),
                    correct_igst_rate=rec.default_igst_rate or Decimal("0.0"),
                )
        return None

    def get_state_name(self, state_code: str, target_date: Optional[date] = None) -> Optional[str]:
        """Look up state name resolved from reference service (single source of truth)."""
        if self.reference_service:
            d = target_date or date(2023, 1, 1)
            res = self.reference_service.resolve_state(state_code, d)
            if res.is_resolved:
                return res.record.state_name
        return None
