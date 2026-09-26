"""
app.investigation.repository.in_memory
======================================
In-memory implementation of the Investigation repository.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from app.investigation.models import (
    BlastRadiusProfile,
    InvestigationProfile,
    RootCauseFinding,
)
class InMemoryInvestigationRepository:
    """Thread-safe in-memory store for investigation intelligence artifacts."""

    def __init__(self) -> None:
        self._root_causes: Dict[str, RootCauseFinding] = {}
        self._blast_radii: Dict[str, BlastRadiusProfile] = {}
        self._investigations: Dict[str, InvestigationProfile] = {}
        self._latest_investigation_id: Optional[str] = None

    def add_root_cause(self, finding: RootCauseFinding) -> None:
        self._root_causes[finding.root_cause_id] = finding

    def add_root_causes(self, findings: List[RootCauseFinding]) -> None:
        for f in findings:
            self._root_causes[f.root_cause_id] = f

    def get_root_cause(self, root_cause_id: str) -> Optional[RootCauseFinding]:
        return self._root_causes.get(root_cause_id)

    def list_root_causes(self) -> List[RootCauseFinding]:
        return list(self._root_causes.values())

    def add_blast_radius(self, profile: BlastRadiusProfile) -> None:
        self._blast_radii[profile.blast_radius_id] = profile

    def get_blast_radius(self, blast_radius_id: str) -> Optional[BlastRadiusProfile]:
        return self._blast_radii.get(blast_radius_id)

    def list_blast_radii(self) -> List[BlastRadiusProfile]:
        return list(self._blast_radii.values())

    def set_investigation_profile(self, profile: InvestigationProfile) -> None:
        self._investigations[profile.investigation_id] = profile
        self._latest_investigation_id = profile.investigation_id

    def get_investigation_profile(self, investigation_id: Optional[str] = None) -> Optional[InvestigationProfile]:
        if investigation_id is not None:
            return self._investigations.get(investigation_id)
        if self._latest_investigation_id:
            return self._investigations.get(self._latest_investigation_id)
        if self._investigations:
            return next(iter(self._investigations.values()))
        return None

    def list_investigations(self) -> List[InvestigationProfile]:
        return list(self._investigations.values())

    def clear(self) -> None:
        self._root_causes.clearハード = {}
        self._root_causes.clear()
        self._blast_radii.clear()
        self._investigations.clear()
        self._latest_investigation_id = None

