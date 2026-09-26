"""
UC15 GST Compliance Agent — Reference Service (Sprint 4)
Centralized enterprise intelligence service providing effective-date resolved statutory references,
audit provenance, and reference snapshots for compliance rules.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
import os
from typing import Any, Dict, List, Optional, Tuple

from app.infrastructure.logging import get_logger
from app.reference.loaders.structured_loader import StructuredReferenceLoader
from app.reference.models.ewb_policy import EWBPolicyReference
from app.reference.models.hsn import HSNReference
from app.reference.models.itc_policy import ITCPolicyReference
from app.reference.models.snapshot import ReferenceSnapshot
from app.reference.models.state import StateReference
from app.reference.models.tax_rate import TaxRateReference
from app.reference.repositories.base import BaseReferenceRepository
from app.reference.repositories.in_memory import InMemoryReferenceRepository
from app.reference.resolvers.effective_date import (
    EffectiveDateResolver,
    ResolutionResult,
    ResolutionStatus,
)

logger = get_logger(__name__)

DEFAULT_REFERENCES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "config",
    "references",
)


class ReferenceService:
    """
    Centralized Reference Intelligence Service.
    Resolves temporal statutory master data, tax rate history, state references,
    and compliance policies for a given transaction date.
    """

    def __init__(
        self,
        repository: Optional[BaseReferenceRepository] = None,
        references_dir: Optional[str] = None,
        auto_load: bool = True,
    ):
        self.repository: BaseReferenceRepository = repository or InMemoryReferenceRepository()
        self.references_dir = references_dir or DEFAULT_REFERENCES_DIR
        self._cache: Dict[Tuple[str, str, str], ResolutionResult] = {}
        
        if auto_load and isinstance(self.repository, InMemoryReferenceRepository):
            self._initialize_data()

    @property
    def repo(self) -> BaseReferenceRepository:
        return self.repository

    def _initialize_data(self) -> None:
        """Load external reference datasets if available, otherwise bootstrap built-in baseline."""
        if os.path.exists(self.references_dir):
            loader = StructuredReferenceLoader(self.repository)
            try:
                loader.load_from_directory(self.references_dir)
            except Exception as e:
                logger.warning(f"Error loading reference files from {self.references_dir}: {e}. Initializing defaults.")
        
        # If still empty, ensure baseline statutory records exist for demo compatibility
        self._ensure_baseline_records()

    def _ensure_baseline_records(self) -> None:
        """Inject baseline statutory reference data if repository is unpopulated."""
        if not self.repository.list_all_states():
            # Standard GST state code table
            states_data = [
                ("01", "Jammu and Kashmir"), ("02", "Himachal Pradesh"), ("03", "Punjab"),
                ("04", "Chandigarh"), ("05", "Uttarakhand"), ("06", "Haryana"),
                ("07", "Delhi"), ("08", "Rajasthan"), ("09", "Uttar Pradesh"),
                ("10", "Bihar"), ("19", "West Bengal"), ("24", "Gujarat"),
                ("27", "Maharashtra"), ("29", "Karnataka"), ("32", "Kerala"),
                ("33", "Tamil Nadu"), ("36", "Telangana"), ("37", "Andhra Pradesh"),
            ]
            for code, name in states_data:
                self.repository.add_state(
                    StateReference(
                        reference_id=f"STATE_{code}",
                        version="1.0",
                        effective_from=date(2017, 7, 1),
                        state_code=code,
                        state_name=name,
                    )
                )

        if not self.repository.list_all_hsn():
            # Standard baseline HSN master from demo dataset
            hsn_data = [
                ("8471", "Automatic data processing machines (Computers and peripherals)", Decimal("0.09"), Decimal("0.09"), Decimal("0.18")),
                ("8409", "Parts of internal combustion engines", Decimal("0.14"), Decimal("0.14"), Decimal("0.28")),
                ("8708", "Parts and accessories of motor vehicles", Decimal("0.14"), Decimal("0.14"), Decimal("0.28")),
                ("8504", "Electrical transformers, static converters", Decimal("0.09"), Decimal("0.09"), Decimal("0.18")),
                ("7210", "Flat-rolled products of iron/steel", Decimal("0.09"), Decimal("0.09"), Decimal("0.18")),
                ("3926", "Other articles of plastics (Plastic Articles NES)", Decimal("0.09"), Decimal("0.09"), Decimal("0.18")),
                ("4011", "New pneumatic tyres, of rubber", Decimal("0.14"), Decimal("0.14"), Decimal("0.28")),
                ("8517", "Telephone sets, smartphones", Decimal("0.09"), Decimal("0.09"), Decimal("0.18")),
                ("8544", "Insulated wire, cable", Decimal("0.09"), Decimal("0.09"), Decimal("0.18")),
                ("9031", "Measuring or checking instruments", Decimal("0.09"), Decimal("0.09"), Decimal("0.18")),
                ("9983", "Other professional, technical and business services", Decimal("0.09"), Decimal("0.09"), Decimal("0.18")),
                ("9954", "General construction services", Decimal("0.09"), Decimal("0.09"), Decimal("0.18")),
                ("9988", "Manufacturing services on physical inputs", Decimal("0.06"), Decimal("0.06"), Decimal("0.12")),
                ("9984", "Telecommunications, broadcasting", Decimal("0.09"), Decimal("0.09"), Decimal("0.18")),
                ("9987", "Maintenance, repair and installation", Decimal("0.09"), Decimal("0.09"), Decimal("0.18")),
            ]
            for code, desc, cgst, sgst, igst in hsn_data:
                self.repository.add_hsn(
                    HSNReference(
                        reference_id=f"HSN_{code}_V1",
                        version="1.0",
                        effective_from=date(2017, 7, 1),
                        code=code,
                        description=desc,
                        default_cgst_rate=cgst,
                        default_sgst_rate=sgst,
                        default_igst_rate=igst,
                    )
                )
                self.repository.add_tax_rate(
                    TaxRateReference(
                        reference_id=f"TAX_{code}_V1",
                        version="1.0",
                        effective_from=date(2017, 7, 1),
                        hsn_code=code,
                        cgst_rate=cgst,
                        sgst_rate=sgst,
                        igst_rate=igst,
                        description=desc,
                    )
                )

        if not self.repository.get_ewb_policy_candidates():
            self.repository.add_ewb_policy(
                EWBPolicyReference(
                    reference_id="EWB_NAT_V1",
                    policy_id="EWB_NAT_001",
                    version="1.0",
                    effective_from=date(2018, 4, 1),
                    name="National E-Way Bill Movement Policy",
                    threshold=Decimal("50000.00"),
                )
            )

        if not self.repository.get_itc_policy_candidates():
            # Section 17(5) blocked credit policies
            policies = [
                ("ITC_17_5_MOTOR", "MOTOR_VEHICLES", ["motor vehicle", "car", "passenger vehicle", "automobile"], "Motor vehicles for transportation of persons (Section 17(5)(a))"),
                ("ITC_17_5_FOOD", "FOOD_BEVERAGES", ["food", "catering", "beverages", "canteen", "restaurant", "meal"], "Food and beverages, outdoor catering (Section 17(5)(b)(i))"),
                ("ITC_17_5_CLUB", "CLUB_MEMBERSHIP", ["club", "membership", "fitness", "gym", "health club"], "Membership of a club, health and fitness centre (Section 17(5)(b)(ii))"),
                ("ITC_17_5_PERSONAL", "PERSONAL_CONSUMPTION", ["personal", "gift", "employee welfare", "free sample"], "Goods or services used for personal consumption (Section 17(5)(g))"),
            ]
            for pol_id, cat, kws, reason in policies:
                self.repository.add_itc_policy(
                    ITCPolicyReference(
                        reference_id=pol_id,
                        policy_id=pol_id,
                        version="1.0",
                        effective_from=date(2017, 7, 1),
                        category=cat,
                        blocked_keywords=kws,
                        is_blocked_17_5=True,
                        blocked_reason=reason,
                    )
                )

    def resolve_hsn(self, code: str, target_date: date) -> ResolutionResult[HSNReference]:
        """Resolve applicable HSN classification valid for the transaction date."""
        cache_key = ("HSN", code.strip(), target_date.isoformat())
        if cache_key in self._cache:
            return self._cache[cache_key]

        candidates = self.repository.get_hsn_candidates(code)
        result = EffectiveDateResolver.resolve(candidates, target_date, entity_label=f"HSN classification '{code}'")
        self._cache[cache_key] = result
        return result

    def resolve_tax_rate(
        self,
        hsn_code: str,
        target_date: date,
        is_interstate: bool = False,
    ) -> ResolutionResult[TaxRateReference]:
        """Resolve applicable statutory tax rate schedule valid for the transaction date."""
        cache_key = ("TAX_RATE", f"{hsn_code.strip()}_{is_interstate}", target_date.isoformat())
        if cache_key in self._cache:
            return self._cache[cache_key]

        candidates = self.repository.get_tax_rate_candidates(hsn_code)
        result = EffectiveDateResolver.resolve(candidates, target_date, entity_label=f"Tax rate for HSN '{hsn_code}'")
        self._cache[cache_key] = result
        return result

    def resolve_state(self, state_code: str, target_date: Optional[date] = None) -> ResolutionResult[StateReference]:
        """Resolve state reference by 2-digit GST state code."""
        d = target_date or date(2023, 1, 1)
        cache_key = ("STATE", state_code.strip(), d.isoformat())
        if cache_key in self._cache:
            return self._cache[cache_key]

        candidates = self.repository.get_state_candidates(state_code)
        result = EffectiveDateResolver.resolve(candidates, d, entity_label=f"State reference for code '{state_code}'")
        self._cache[cache_key] = result
        return result

    def resolve_ewb_policy(
        self,
        target_date: date,
        state_code: Optional[str] = None,
    ) -> ResolutionResult[EWBPolicyReference]:
        """
        Resolve statutory E-Way Bill policy valid for date and jurisdiction.
        Implements historical fallback: if a state-specific policy exists but was not active
        on target_date, gracefully falls back to the national policy active on that date.
        """
        clean_state = str(state_code).strip().zfill(2) if state_code else None
        cache_key = ("EWB", clean_state or "NATIONAL", target_date.isoformat())
        if cache_key in self._cache:
            return self._cache[cache_key]

        if clean_state:
            state_candidates = self.repository.get_state_ewb_policies(clean_state)
            if state_candidates:
                state_res = EffectiveDateResolver.resolve(
                    state_candidates,
                    target_date,
                    entity_label=f"State E-Way Bill Policy ({clean_state})",
                )
                if state_res.is_resolved or state_res.is_conflict:
                    self._cache[cache_key] = state_res
                    return state_res
                # State policy candidates exist but NONE were active on target_date (e.g. before starts or after ends)
                # Fall back to national policy active on target_date!
                national_candidates = self.repository.get_national_ewb_policies()
                nat_res = EffectiveDateResolver.resolve(
                    national_candidates,
                    target_date,
                    entity_label="National E-Way Bill Policy",
                )
                if nat_res.is_resolved:
                    fallback_res = ResolutionResult(
                        status=nat_res.status,
                        resolution_date=nat_res.resolution_date,
                        reference=nat_res.reference,
                        reference_id=nat_res.reference_id,
                        reference_version=nat_res.reference_version,
                        effective_from=nat_res.effective_from,
                        effective_to=nat_res.effective_to,
                        source=nat_res.source,
                        reason=f"Fell back to national EWB policy for state {clean_state} on {target_date}: {nat_res.reason}",
                        candidates=nat_res.candidates,
                    )
                    self._cache[cache_key] = fallback_res
                    return fallback_res
                self._cache[cache_key] = nat_res
                return nat_res

        national_candidates = self.repository.get_national_ewb_policies()
        res = EffectiveDateResolver.resolve(
            national_candidates,
            target_date,
            entity_label="National E-Way Bill Policy",
        )
        self._cache[cache_key] = res
        return res

    def resolve_itc_policy(
        self,
        item_desc: str,
        target_date: date,
    ) -> ResolutionResult[ITCPolicyReference]:
        """
        Resolve applicable ITC restriction policy based on line item description and date.
        Distinguishes:
          - Missing ITC reference catalog -> NOT_FOUND (reason: catalog unavailable)
          - Multiple conflicting versions of the same policy -> CONFLICT
          - Matches active blocked category -> RESOLVED (with matched policy)
          - Does not match any blocked category -> NOT_FOUND (reason: No Section 17(5) applies)
        """
        candidates = self.repository.get_itc_policy_candidates()
        if not candidates:
            return ResolutionResult(
                status=ResolutionStatus.NOT_FOUND,
                resolution_date=target_date,
                reason="No statutory ITC reference policy records exist in repository.",
            )

        active_candidates = [p for p in candidates if p.is_active_on(target_date)]
        if not active_candidates:
            return ResolutionResult(
                status=ResolutionStatus.NOT_FOUND,
                resolution_date=target_date,
                reason=f"No active statutory ITC reference policy found for transaction date {target_date}.",
                candidates=candidates,
            )

        matching_policies: List[ITCPolicyReference] = [
            p for p in active_candidates if p.matches_item_description(item_desc)
        ]

        if not matching_policies:
            return ResolutionResult(
                status=ResolutionStatus.NOT_FOUND,
                resolution_date=target_date,
                reason="No Section 17(5) blocked credit restriction applies to this item description.",
                candidates=active_candidates,
            )

        # Check for multiple active versions of the same policy_id (conflict)
        policy_ids = {p.policy_id for p in matching_policies}
        for pid in policy_ids:
            same_id = [p for p in matching_policies if p.policy_id == pid]
            if len(same_id) > 1:
                return ResolutionResult(
                    status=ResolutionStatus.CONFLICT,
                    resolution_date=target_date,
                    reason=f"ITC policy conflict: multiple active versions found for policy '{pid}' on {target_date}.",
                    candidates=same_id,
                )

        # Matched one or more distinct active blocked categories
        match = matching_policies[0]
        return ResolutionResult(
            status=ResolutionStatus.RESOLVED,
            resolution_date=target_date,
            reference=match,
            reference_id=match.reference_id,
            reference_version=match.version,
            effective_from=match.effective_from,
            effective_to=match.effective_to,
            source=match.source,
            reason=f"Resolved Section 17(5) blocked credit policy '{match.policy_id}'.",
            candidates=matching_policies,
        )

    def create_snapshot(self, invoice_id: str, transaction_date: date) -> ReferenceSnapshot:
        """Create an empty snapshot initialized for an invoice audit record."""
        return ReferenceSnapshot(
            invoice_id=invoice_id,
            transaction_date=str(transaction_date),
        )

    def clear_cache(self) -> None:
        """Clear resolution memoization cache."""
        self._cache.clear()
