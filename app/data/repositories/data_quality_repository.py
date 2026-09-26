"""
app.data.repositories.data_quality_repository
==============================================
Data Quality & Ingestion Repository for UC15 (Sprint 17).
Provides repository abstraction with both InMemory and PostgreSQL/SQLAlchemy implementations.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.data.lineage.lineage_tracker import DataLineageRecord, TransformationStep
from app.data.quality.quality_engine import DataQualityReport, QualityStatus, RecordQualityResult
from app.db.models import (
    DataLineageRecordORM,
    DataQualityReportORM,
    IngestionJobORM,
    IngestionRecordORM,
)
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class DataQualityRepository(ABC):
    """Abstract repository contract for Ingestion Jobs, Records, Quality Reports, and Data Lineage."""

    @abstractmethod
    def save_ingestion_job(self, job_dict: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def get_ingestion_job(self, ingestion_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_ingestion_jobs(
        self, tenant_id: str = "tenant_default", status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_record_result(self, record: RecordQualityResult, ingestion_id: str, tenant_id: str, raw_data: Dict[str, Any], norm_data: Dict[str, Any], fingerprint: str) -> None:
        pass

    @abstractmethod
    def list_records_for_job(self, ingestion_id: str) -> List[RecordQualityResult]:
        pass

    @abstractmethod
    def save_quality_report(self, report: DataQualityReport) -> None:
        pass

    @abstractmethod
    def get_quality_report(self, ingestion_id: str) -> Optional[DataQualityReport]:
        pass

    @abstractmethod
    def save_lineage_record(self, lineage: DataLineageRecord) -> None:
        pass

    @abstractmethod
    def get_lineage_record(self, canonical_record_id: str) -> Optional[DataLineageRecord]:
        pass

    @abstractmethod
    def list_existing_fingerprints(self, tenant_id: str = "tenant_default") -> Tuple[Dict[str, str], Dict[str, str]]:
        """Return (exact_fingerprints_map, potential_fingerprints_map)."""
        pass


class InMemoryDataQualityRepository(DataQualityRepository):
    """In-memory implementation of DataQualityRepository with shared in-process state."""
    _SHARED_JOBS: Dict[str, Dict[str, Any]] = {}
    _SHARED_RECORDS: Dict[str, List[RecordQualityResult]] = {}
    _SHARED_RECORD_DETAILS: Dict[str, Dict[str, Any]] = {}
    _SHARED_REPORTS: Dict[str, DataQualityReport] = {}
    _SHARED_LINEAGES: Dict[str, DataLineageRecord] = {}
    _SHARED_EXACT_FPS: Dict[str, str] = {}
    _SHARED_POTENTIAL_FPS: Dict[str, str] = {}

    def __init__(self):
        self._jobs = self._SHARED_JOBS
        self._records = self._SHARED_RECORDS
        self._record_details = self._SHARED_RECORD_DETAILS
        self._reports = self._SHARED_REPORTS
        self._lineages = self._SHARED_LINEAGES
        self._exact_fps = self._SHARED_EXACT_FPS
        self._potential_fps = self._SHARED_POTENTIAL_FPS

    def save_ingestion_job(self, job_dict: Dict[str, Any]) -> None:
        self._jobs[job_dict["ingestion_id"]] = job_dict

    def get_ingestion_job(self, ingestion_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(ingestion_id)

    def list_ingestion_jobs(
        self, tenant_id: str = "tenant_default", status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = [j for j in self._jobs.values() if j.get("tenant_id") == tenant_id]
        if status:
            results = [j for j in results if j.get("status") == status]
        return results

    def save_record_result(
        self, record: RecordQualityResult, ingestion_id: str, tenant_id: str, raw_data: Dict[str, Any], norm_data: Dict[str, Any], fingerprint: str
    ) -> None:
        if ingestion_id not in self._records:
            self._records[ingestion_id] = []
        self._records[ingestion_id].append(record)
        self._record_details[record.record_id] = {
            "record": record,
            "ingestion_id": ingestion_id,
            "tenant_id": tenant_id,
            "raw_data": raw_data,
            "norm_data": norm_data,
            "fingerprint": fingerprint,
        }

    def list_records_for_job(self, ingestion_id: str) -> List[RecordQualityResult]:
        return self._records.get(ingestion_id, [])

    def save_quality_report(self, report: DataQualityReport) -> None:
        self._reports[report.ingestion_id] = report

    def get_quality_report(self, ingestion_id: str) -> Optional[DataQualityReport]:
        return self._reports.get(ingestion_id)

    def save_lineage_record(self, lineage: DataLineageRecord) -> None:
        self._lineages[lineage.canonical_record_id] = lineage

    def get_lineage_record(self, canonical_record_id: str) -> Optional[DataLineageRecord]:
        return self._lineages.get(canonical_record_id)

    def list_existing_fingerprints(self, tenant_id: str = "tenant_default") -> Tuple[Dict[str, str], Dict[str, str]]:
        return dict(self._exact_fps), dict(self._potential_fps)

    def register_fingerprint(self, exact_fp: str, potential_fp: str, record_id: str) -> None:
        if exact_fp:
            self._exact_fps[exact_fp] = record_id
        if potential_fp:
            self._potential_fps[potential_fp] = record_id


class SQLAlchemyDataQualityRepository(DataQualityRepository):
    """PostgreSQL / SQLAlchemy implementation of DataQualityRepository."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def save_ingestion_job(self, job_dict: Dict[str, Any]) -> None:
        with self.session_factory() as session:
            existing = session.query(IngestionJobORM).filter_by(ingestion_id=job_dict["ingestion_id"]).first()
            if existing:
                existing.status = job_dict.get("status", existing.status)
                existing.completed_at = job_dict.get("completed_at", existing.completed_at)
                existing.total_records = job_dict.get("total_records", existing.total_records)
                existing.accepted_records = job_dict.get("accepted_records", existing.accepted_records)
                existing.rejected_records = job_dict.get("rejected_records", existing.rejected_records)
                existing.duplicate_records = job_dict.get("duplicate_records", existing.duplicate_records)
                existing.warning_records = job_dict.get("warning_records", existing.warning_records)
                existing.quality_score = job_dict.get("quality_score", existing.quality_score)
                existing.error_summary_json = json.dumps(job_dict.get("error_summary", []))
            else:
                orm = IngestionJobORM(
                    ingestion_id=job_dict["ingestion_id"],
                    source_id=job_dict["source_id"],
                    tenant_id=job_dict.get("tenant_id", "tenant_default"),
                    dataset_type=job_dict.get("dataset_type", "INVOICES"),
                    started_at=job_dict["started_at"],
                    completed_at=job_dict.get("completed_at"),
                    status=job_dict.get("status", "PENDING"),
                    total_records=job_dict.get("total_records", 0),
                    accepted_records=job_dict.get("accepted_records", 0),
                    rejected_records=job_dict.get("rejected_records", 0),
                    duplicate_records=job_dict.get("duplicate_records", 0),
                    warning_records=job_dict.get("warning_records", 0),
                    quality_score=job_dict.get("quality_score", 0.0),
                    error_summary_json=json.dumps(job_dict.get("error_summary", [])),
                    created_by=job_dict.get("created_by", "SYSTEM"),
                    correlation_id=job_dict.get("correlation_id"),
                )
                session.add(orm)
            session.commit()

    def get_ingestion_job(self, ingestion_id: str) -> Optional[Dict[str, Any]]:
        with self.session_factory() as session:
            orm = session.query(IngestionJobORM).filter_by(ingestion_id=ingestion_id).first()
            if not orm:
                return None
            return {
                "ingestion_id": orm.ingestion_id,
                "source_id": orm.source_id,
                "tenant_id": orm.tenant_id,
                "dataset_type": orm.dataset_type,
                "started_at": orm.started_at,
                "completed_at": orm.completed_at,
                "status": orm.status,
                "total_records": orm.total_records,
                "accepted_records": orm.accepted_records,
                "rejected_records": orm.rejected_records,
                "duplicate_records": orm.duplicate_records,
                "warning_records": orm.warning_records,
                "quality_score": orm.quality_score,
                "error_summary": json.loads(orm.error_summary_json or "[]"),
                "created_by": orm.created_by,
                "correlation_id": orm.correlation_id,
            }

    def list_ingestion_jobs(
        self, tenant_id: str = "tenant_default", status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self.session_factory() as session:
            query = session.query(IngestionJobORM).filter_by(tenant_id=tenant_id)
            if status:
                query = query.filter_by(status=status)
            results = []
            for orm in query.all():
                results.append({
                    "ingestion_id": orm.ingestion_id,
                    "source_id": orm.source_id,
                    "tenant_id": orm.tenant_id,
                    "dataset_type": orm.dataset_type,
                    "started_at": orm.started_at,
                    "completed_at": orm.completed_at,
                    "status": orm.status,
                    "total_records": orm.total_records,
                    "accepted_records": orm.accepted_records,
                    "rejected_records": orm.rejected_records,
                    "duplicate_records": orm.duplicate_records,
                    "warning_records": orm.warning_records,
                    "quality_score": orm.quality_score,
                    "created_by": orm.created_by,
                })
            return results

    def save_record_result(
        self, record: RecordQualityResult, ingestion_id: str, tenant_id: str, raw_data: Dict[str, Any], norm_data: Dict[str, Any], fingerprint: str
    ) -> None:
        with self.session_factory() as session:
            import datetime
            orm = IngestionRecordORM(
                record_id=record.record_id,
                ingestion_id=ingestion_id,
                record_index=record.record_index,
                source_record_id=str(record.record_index),
                tenant_id=tenant_id,
                status=record.status,
                raw_data_json=json.dumps(raw_data),
                normalized_data_json=json.dumps(norm_data),
                quality_score=record.quality_score,
                duplicate_status=record.duplicate_status,
                fingerprint=fingerprint,
                validation_errors_json=json.dumps(record.errors),
                validation_warnings_json=json.dumps(record.warnings),
                transformation_log_json=json.dumps(record.normalized_fields),
                created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            )
            session.merge(orm)
            session.commit()

    def list_records_for_job(self, ingestion_id: str) -> List[RecordQualityResult]:
        with self.session_factory() as session:
            orms = session.query(IngestionRecordORM).filter_by(ingestion_id=ingestion_id).all()
            results = []
            for orm in orms:
                results.append(
                    RecordQualityResult(
                        record_id=orm.record_id,
                        record_index=orm.record_index,
                        quality_score=orm.quality_score,
                        status=orm.status,
                        dimension_scores={},
                        errors=json.loads(orm.validation_errors_json or "[]"),
                        warnings=json.loads(orm.validation_warnings_json or "[]"),
                        normalized_fields=json.loads(orm.transformation_log_json or "[]"),
                        duplicate_status=orm.duplicate_status,
                        validation_status="INVALID" if (orm.validation_errors_json and json.loads(orm.validation_errors_json)) else "VALID",
                    )
                )
            return results

    def save_quality_report(self, report: DataQualityReport) -> None:
        with self.session_factory() as session:
            orm = DataQualityReportORM(
                report_id=f"RPT-{report.ingestion_id}",
                ingestion_id=report.ingestion_id,
                overall_quality_score=report.overall_quality_score,
                quality_status=report.quality_status.value,
                dimension_scores_json=json.dumps(report.dimension_scores),
                total_records=report.total_records,
                accepted_records=report.accepted_records,
                rejected_records=report.rejected_records,
                duplicate_records=report.duplicate_records,
                warning_records=report.warning_records,
                issues_json=json.dumps(report.issues),
                warnings_json=json.dumps(report.warnings),
                created_at=report.created_at,
            )
            session.merge(orm)
            session.commit()

    def get_quality_report(self, ingestion_id: str) -> Optional[DataQualityReport]:
        with self.session_factory() as session:
            orm = session.query(DataQualityReportORM).filter_by(ingestion_id=ingestion_id).first()
            if not orm:
                return None
            return DataQualityReport(
                ingestion_id=orm.ingestion_id,
                overall_quality_score=orm.overall_quality_score,
                quality_status=QualityStatus(orm.quality_status),
                dimension_scores=json.loads(orm.dimension_scores_json),
                total_records=orm.total_records,
                accepted_records=orm.accepted_records,
                rejected_records=orm.rejected_records,
                duplicate_records=orm.duplicate_records,
                warning_records=orm.warning_records,
                issues=json.loads(orm.issues_json or "[]"),
                warnings=json.loads(orm.warnings_json or "[]"),
                created_at=orm.created_at,
            )

    def save_lineage_record(self, lineage: DataLineageRecord) -> None:
        with self.session_factory() as session:
            orm = DataLineageRecordORM(
                lineage_id=lineage.lineage_id,
                ingestion_id=lineage.ingestion_id,
                source_id=lineage.source_id,
                source_record_id=lineage.source_record_id,
                canonical_record_id=lineage.canonical_record_id,
                tenant_id=lineage.tenant_id,
                transformations_json=json.dumps([t.to_dict() for t in lineage.transformations]),
                downstream_evidence_ids_json=json.dumps(lineage.downstream_evidence_ids),
                downstream_finding_ids_json=json.dumps(lineage.downstream_finding_ids),
                downstream_case_id=lineage.downstream_case_id,
                created_at=lineage.created_at,
            )
            session.merge(orm)
            session.commit()

    def get_lineage_record(self, canonical_record_id: str) -> Optional[DataLineageRecord]:
        with self.session_factory() as session:
            orm = session.query(DataLineageRecordORM).filter_by(canonical_record_id=canonical_record_id).first()
            if not orm:
                return None
            trans_list = [
                TransformationStep(
                    step_name=t["step_name"],
                    input_value=t["input_value"],
                    output_value=t["output_value"],
                    description=t["description"],
                    timestamp=t.get("timestamp", ""),
                )
                for t in json.loads(orm.transformations_json or "[]")
            ]
            return DataLineageRecord(
                lineage_id=orm.lineage_id,
                ingestion_id=orm.ingestion_id,
                source_id=orm.source_id,
                source_record_id=orm.source_record_id,
                canonical_record_id=orm.canonical_record_id,
                tenant_id=orm.tenant_id,
                transformations=trans_list,
                downstream_evidence_ids=json.loads(orm.downstream_evidence_ids_json or "[]"),
                downstream_finding_ids=json.loads(orm.downstream_finding_ids_json or "[]"),
                downstream_case_id=orm.downstream_case_id,
                created_at=orm.created_at,
            )

    def list_existing_fingerprints(self, tenant_id: str = "tenant_default") -> Tuple[Dict[str, str], Dict[str, str]]:
        with self.session_factory() as session:
            orms = session.query(IngestionRecordORM).filter_by(tenant_id=tenant_id).all()
            exact_fps = {}
            potential_fps = {}
            for o in orms:
                if o.fingerprint:
                    exact_fps[o.fingerprint] = o.record_id
            return exact_fps, potential_fps
