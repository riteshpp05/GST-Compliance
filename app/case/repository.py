"""
app.case.repository
===================
Repository abstraction layer for Investigation Cases (Sprint 13 & Sprint 15).
Architected with abstract BaseCaseRepository interface to enable seamless PostgreSQL migration.
Provides thread-safe InMemoryCaseRepository and SQLAlchemyCaseRepository.
"""

from __future__ import annotations

import json
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union
from app.case.models import (
    CaseEvidenceReference,
    CaseEvent,
    InvestigationCase,
    InvestigationPlanDomain,
    CaseEvidenceRecord,
    CaseFinding,
    CaseRiskAssessment,
    CaseRecommendation,
)
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

_case_repository: Optional[BaseCaseRepository] = None


class BaseCaseRepository(ABC):
    """Abstract Repository interface for Case Management & Enterprise Workflow."""

    @abstractmethod
    def save_case(self, case: InvestigationCase) -> None:
        pass

    @abstractmethod
    def get_case(self, case_id: str) -> Optional[InvestigationCase]:
        pass

    @abstractmethod
    def list_cases(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        invoice_id: Optional[str] = None,
    ) -> List[InvestigationCase]:
        pass

    @abstractmethod
    def delete_case(self, case_id: str) -> bool:
        pass

    @abstractmethod
    def save_event(self, event: CaseEvent) -> None:
        pass

    @abstractmethod
    def get_events(self, case_id: str) -> List[CaseEvent]:
        pass

    @abstractmethod
    def save_evidence_ref(self, case_id: str, ref: CaseEvidenceReference) -> None:
        pass

    @abstractmethod
    def get_evidence_refs(self, case_id: str) -> List[CaseEvidenceReference]:
        pass

    @abstractmethod
    def save_plan(self, plan: InvestigationPlanDomain) -> None:
        pass

    @abstractmethod
    def get_plan(self, case_id: str) -> Optional[InvestigationPlanDomain]:
        pass

    @abstractmethod
    def save_evidence_record(self, record: CaseEvidenceRecord) -> None:
        pass

    @abstractmethod
    def get_evidence_records(self, case_id: str) -> List[CaseEvidenceRecord]:
        pass

    @abstractmethod
    def save_finding(self, finding: CaseFinding) -> None:
        pass

    @abstractmethod
    def get_findings(self, case_id: str) -> List[CaseFinding]:
        pass

    @abstractmethod
    def save_risk_assessment(self, assessment: CaseRiskAssessment) -> None:
        pass

    @abstractmethod
    def get_risk_assessment(self, case_id: str) -> Optional[CaseRiskAssessment]:
        pass

    @abstractmethod
    def save_recommendation(self, recommendation: CaseRecommendation) -> None:
        pass

    @abstractmethod
    def get_recommendation(self, case_id: str) -> Optional[CaseRecommendation]:
        pass


class InMemoryCaseRepository(BaseCaseRepository):
    """Thread-safe in-memory repository implementation for Sprint 13 & 15 with optional JSON persistence."""

    def __init__(self, persistence_file: Optional[Union[Path, str]] = None) -> None:
        self._cases: Dict[str, InvestigationCase] = {}
        self._events: Dict[str, List[CaseEvent]] = {}
        self._evidence: Dict[str, List[CaseEvidenceReference]] = {}
        self._plans: Dict[str, InvestigationPlanDomain] = {}
        self._evidence_records: Dict[str, List[CaseEvidenceRecord]] = {}
        self._findings: Dict[str, List[CaseFinding]] = {}
        self._risk_assessments: Dict[str, CaseRiskAssessment] = {}
        self._recommendations: Dict[str, CaseRecommendation] = {}
        self._lock = threading.RLock()
        self._persistence_file: Optional[Path] = Path(persistence_file) if persistence_file else None
        if self._persistence_file and self._persistence_file.exists():
            self._load_from_disk()

    def _save_to_disk(self) -> None:
        if not self._persistence_file:
            return
        try:
            self._persistence_file.parent.mkdir(parents=True, exist_ok=True)
            cases_dict = {cid: case.model_dump() for cid, case in self._cases.items()}
            tmp_file = self._persistence_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(cases_dict, f, indent=2, default=str)
            tmp_file.replace(self._persistence_file)
        except Exception as e:
            logger.warning(f"Could not persist cases to disk: {e}")

    def _load_from_disk(self) -> None:
        if not self._persistence_file or not self._persistence_file.exists():
            return
        try:
            with open(self._persistence_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for cid, cdata in data.items():
                    try:
                        case = InvestigationCase.model_validate(cdata)
                        self._cases[case.case_id] = case
                    except Exception as parse_err:
                        logger.warning(f"Failed to load case {cid} from disk: {parse_err}")
        except Exception as e:
            logger.warning(f"Could not load cases from disk: {e}")

    def save_case(self, case: InvestigationCase) -> None:
        with self._lock:
            self._cases[case.case_id] = case
            self._save_to_disk()

    def get_case(self, case_id: str) -> Optional[InvestigationCase]:
        with self._lock:
            return self._cases.get(case_id)

    def list_cases(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        invoice_id: Optional[str] = None,
    ) -> List[InvestigationCase]:
        with self._lock:
            result = list(self._cases.values())
            if status:
                result = [c for c in result if (hasattr(c.status, "value") and c.status.value == status) or c.status == status]
            if priority:
                result = [c for c in result if c.priority == priority]
            if invoice_id:
                result = [c for c in result if c.invoice_id == invoice_id]
            return result

    def delete_case(self, case_id: str) -> bool:
        with self._lock:
            if case_id in self._cases:
                del self._cases[case_id]
                self._events.pop(case_id, None)
                self._evidence.pop(case_id, None)
                self._plans.pop(case_id, None)
                self._evidence_records.pop(case_id, None)
                self._findings.pop(case_id, None)
                self._risk_assessments.pop(case_id, None)
                self._recommendations.pop(case_id, None)
                self._save_to_disk()
                return True
            return False

    def save_event(self, event: CaseEvent) -> None:
        with self._lock:
            if event.case_id not in self._events:
                self._events[event.case_id] = []
            self._events[event.case_id].append(event)

    def get_events(self, case_id: str) -> List[CaseEvent]:
        with self._lock:
            return list(self._events.get(case_id, []))

    def save_evidence_ref(self, case_id: str, ref: CaseEvidenceReference) -> None:
        with self._lock:
            if case_id not in self._evidence:
                self._evidence[case_id] = []
            self._evidence[case_id].append(ref)

    def get_evidence_refs(self, case_id: str) -> List[CaseEvidenceReference]:
        with self._lock:
            return list(self._evidence.get(case_id, []))

    def save_plan(self, plan: InvestigationPlanDomain) -> None:
        with self._lock:
            self._plans[plan.case_id] = plan

    def get_plan(self, case_id: str) -> Optional[InvestigationPlanDomain]:
        with self._lock:
            return self._plans.get(case_id)

    def save_evidence_record(self, record: CaseEvidenceRecord) -> None:
        with self._lock:
            if record.case_id not in self._evidence_records:
                self._evidence_records[record.case_id] = []
            self._evidence_records[record.case_id].append(record)

    def get_evidence_records(self, case_id: str) -> List[CaseEvidenceRecord]:
        with self._lock:
            return list(self._evidence_records.get(case_id, []))

    def save_finding(self, finding: CaseFinding) -> None:
        with self._lock:
            if finding.case_id not in self._findings:
                self._findings[finding.case_id] = []
            self._findings[finding.case_id].append(finding)

    def get_findings(self, case_id: str) -> List[CaseFinding]:
        with self._lock:
            return list(self._findings.get(case_id, []))

    def save_risk_assessment(self, assessment: CaseRiskAssessment) -> None:
        with self._lock:
            self._risk_assessments[assessment.case_id] = assessment

    def get_risk_assessment(self, case_id: str) -> Optional[CaseRiskAssessment]:
        with self._lock:
            return self._risk_assessments.get(case_id)

    def save_recommendation(self, recommendation: CaseRecommendation) -> None:
        with self._lock:
            self._recommendations[recommendation.case_id] = recommendation

    def get_recommendation(self, case_id: str) -> Optional[CaseRecommendation]:
        with self._lock:
            return self._recommendations.get(case_id)


def get_case_repository(persistence_file: Optional[Union[Path, str]] = None) -> BaseCaseRepository:
    global _case_repository
    if _case_repository is None:
        from app.db.connection import is_db_configured
        if is_db_configured():
            from app.case.sqlalchemy_case_repository import SQLAlchemyCaseRepository
            _case_repository = SQLAlchemyCaseRepository()
        else:
            default_path = Path(__file__).resolve().parent.parent.parent / "data" / "cases_store.json"
            _case_repository = InMemoryCaseRepository(persistence_file=persistence_file or default_path)
    return _case_repository


def reset_case_repository() -> None:
    global _case_repository
    _case_repository = None
