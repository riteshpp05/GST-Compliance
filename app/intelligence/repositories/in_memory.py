"""
app.intelligence.repositories.in_memory
=======================================
In-memory implementation of BaseIntelligenceRepository with indexed lookups.
Provides fast querying by invoice ID, category, and finding type.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from app.intelligence.anomaly.models import AnomalyFinding
from app.intelligence.common.enums import IntelligenceCategory
from app.intelligence.common.models import IntelligenceFinding
from app.intelligence.duplicate.models import DuplicateCandidate, DuplicateCluster
class InMemoryIntelligenceRepository:
    """
    In-memory store for Intelligence findings, duplicate candidates,
    clusters, and anomaly evaluations.
    """

    def __init__(self) -> None:
        self._findings: Dict[str, IntelligenceFinding] = {}
        self._by_invoice: Dict[str, List[str]] = defaultdict(list)
        self._by_category: Dict[IntelligenceCategory, List[str]] = defaultdict(list)

        self._duplicate_candidates: List[DuplicateCandidate] = []
        self._duplicate_clusters: List[DuplicateCluster] = []
        self._anomaly_findings: List[AnomalyFinding] = []

    def add_finding(self, finding: IntelligenceFinding) -> None:
        fid = finding.finding_id
        self._findings[fid] = finding

        if finding.invoice_id:
            self._by_invoice[finding.invoice_id].append(fid)

        self._by_category[finding.category].append(fid)

    def add_findings(self, findings: List[IntelligenceFinding]) -> None:
        for f in findings:
            self.add_finding(f)

    def get_finding(self, finding_id: str) -> Optional[IntelligenceFinding]:
        return self._findings.get(finding_id)

    def get_findings_by_invoice(self, invoice_id: str) -> List[IntelligenceFinding]:
        ids = self._by_invoice.get(invoice_id, [])
        return [self._findings[fid] for fid in ids if fid in self._findings]

    def get_findings_by_category(self, category: IntelligenceCategory) -> List[IntelligenceFinding]:
        ids = self._by_category.get(category, [])
        return [self._findings[fid] for fid in ids if fid in self._findings]

    def list_all_findings(self) -> List[IntelligenceFinding]:
        return list(self._findings.values())

    def add_duplicate_candidates(self, candidates: List[DuplicateCandidate]) -> None:
        self._duplicate_candidates.extend(candidates)

    def list_duplicate_candidates(self) -> List[DuplicateCandidate]:
        return list(self._duplicate_candidates)

    def add_duplicate_clusters(self, clusters: List[DuplicateCluster]) -> None:
        self._duplicate_clusters.extend(clusters)

    def list_duplicate_clusters(self) -> List[DuplicateCluster]:
        return list(self._duplicate_clusters)

    def add_anomaly_findings(self, findings: List[AnomalyFinding]) -> None:
        self._anomaly_findings.extend(findings)

    def list_anomaly_findings(self) -> List[AnomalyFinding]:
        return list(self._anomaly_findings)

    def clear(self) -> None:
        self._findings.clear()
        self._by_invoice.clear()
        self._by_category.clear()
        self._duplicate_candidates.clear()
        self._duplicate_clusters.clear()
        self._anomaly_findings.clear()

