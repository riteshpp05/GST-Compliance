"""
app.investigation.root_cause.engine
===================================
Root Cause Intelligence Engine (Sprint 8).
Executes deterministic candidate generation, multi-dimensional scoring,
ranking, primary root cause designation, and contributing factor separation.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from app.investigation.config.investigation_config import (
    InvestigationConfig,
    default_investigation_config,
)
from app.investigation.enums import RootCauseConfidence, RootCauseStatus, RootCauseType
from app.investigation.evidence.models import EvidenceContext
from app.investigation.models import RootCauseFinding
from app.investigation.root_cause.candidates import CandidateGenerator
from app.investigation.root_cause.scorer import RootCauseScorer


class RootCauseEngine:
    """
    Core engine for identifying, ranking, and explaining root causes.
    Separates Primary Root Cause from Contributing Factors without forcing a single cause.
    """

    def __init__(
        self,
        config: Optional[InvestigationConfig] = None,
        candidate_generator: Optional[CandidateGenerator] = None,
        scorer: Optional[RootCauseScorer] = None,
    ) -> None:
        self.config = config or default_investigation_config
        self.scorer = scorer or RootCauseScorer(config=self.config)
        self.candidate_generator = candidate_generator or CandidateGenerator(
            config=self.config,
            scorer=self.scorer,
        )

    def analyze(
        self,
        ctx: EvidenceContext,
    ) -> Tuple[Optional[RootCauseFinding], List[RootCauseFinding]]:
        """
        Analyze the evidence context and return (primary_root_cause, ranked_candidates).
        """
        candidates = self.candidate_generator.generate_candidates(ctx)

        if not candidates:
            return None, []

        # Sort strictly by total score descending, then by affected count descending
        ranked = sorted(
            candidates,
            key=lambda c: (c.score.total_score, len(c.affected_invoice_ids)),
            reverse=True,
        )

        primary = ranked[0] if ranked else None

        return primary, ranked
