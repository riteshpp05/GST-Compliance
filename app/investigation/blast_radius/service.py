"""
app.investigation.blast_radius.service
======================================
Service layer for Blast Radius Intelligence.
Provides APIs for evaluating impact boundaries of root causes or arbitrary invoice cohorts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from app.investigation.blast_radius.engine import BlastRadiusEngine
from app.investigation.config.investigation_config import (
    InvestigationConfig,
    default_investigation_config,
)
from app.investigation.evidence.models import EvidenceContext
from app.investigation.models import BlastRadiusProfile, RootCauseFinding


class BlastRadiusService:
    """
    High-level service interface for Blast Radius calculations.
    """

    def __init__(
        self,
        config: Optional[InvestigationConfig] = None,
        engine: Optional[BlastRadiusEngine] = None,
    ) -> None:
        self.config = config or default_investigation_config
        self.engine = engine or BlastRadiusEngine(config=self.config)

    def evaluate_blast_radius(
        self,
        ctx: EvidenceContext,
        target_invoice_ids: Set[str],
        root_cause_id: str = "GENERIC_INVESTIGATION",
    ) -> BlastRadiusProfile:
        """Compute blast radius profile for a target set of invoice IDs."""
        return self.engine.calculate_profile(
            ctx=ctx,
            target_invoice_ids=target_invoice_ids,
            root_cause_id=root_cause_id,
        )

    def evaluate_for_root_cause(
        self,
        ctx: EvidenceContext,
        root_cause: RootCauseFinding,
    ) -> BlastRadiusProfile:
        """Compute blast radius specifically for an identified root-cause finding."""
        target_ids = set(root_cause.affected_invoice_ids)
        return self.engine.calculate_profile(
            ctx=ctx,
            target_invoice_ids=target_ids,
            root_cause_id=root_cause.root_cause_id,
        )
