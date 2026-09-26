"""
app.data.service
================
Data Ingestion & Quality Service Orchestrator for UC15 (Sprint 17).
Orchestrates Source -> Ingestion -> Schema Validation -> Normalization -> Deduplication -> Data Quality -> Canonical Storage -> Lineage -> Existing Intelligence Integration.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.case.service import CaseService, get_case_service
from app.data.deduplication import DeduplicationEngine, DuplicateStatus
from app.data.lineage import DataLineageRecord, LineageTracker, TransformationStep
from app.data.normalization.invoice_normalizer import InvoiceNormalizer
from app.data.quality import DataQualityEngine, DataQualityReport, QualityStatus, RecordQualityResult
from app.data.repositories.data_quality_repository import (
    DataQualityRepository,
    InMemoryDataQualityRepository,
    SQLAlchemyDataQualityRepository,
)
from app.data.repositories.invoice_repository import InvoiceRepository, InMemoryInvoiceRepository
from app.data.sources import DataSource, DataSourceMetadata
from app.data.validation import SchemaValidator
from app.db.connection import get_sessionmaker, is_db_configured
from app.domain.models.ingestion import IngestionStatus, SourceMetadata
from app.domain.models.invoice import Invoice
from app.infrastructure.logging import get_logger
from app.security import (
    AuthenticatedPrincipal,
    CaseAccessControl,
    PermissionEnum,
    PermissionEvaluator,
    get_internal_compatibility_principal,
)
from app.security.exceptions import ForbiddenException

logger = get_logger(__name__)

_GLOBAL_DATA_SERVICE: Optional[DataIngestionService] = None


def get_data_ingestion_service() -> DataIngestionService:
    """Singleton getter for DataIngestionService."""
    global _GLOBAL_DATA_SERVICE
    if _GLOBAL_DATA_SERVICE is None:
        if is_db_configured():
            factory = get_sessionmaker()
            repo = SQLAlchemyDataQualityRepository(session_factory=factory)
        else:
            repo = InMemoryDataQualityRepository()
        _GLOBAL_DATA_SERVICE = DataIngestionService(repository=repo)
    return _GLOBAL_DATA_SERVICE


def reset_data_ingestion_service() -> None:
    """Reset singleton instance of DataIngestionService."""
    global _GLOBAL_DATA_SERVICE
    _GLOBAL_DATA_SERVICE = None


class DataIngestionService:
    """
    Primary Application Service for Data Ingestion, Schema Validation,
    Normalization, Deduplication, Data Quality Scoring, and Provenance Lineage.
    """

    def __init__(
        self,
        repository: Optional[DataQualityRepository] = None,
        invoice_repository: Optional[InvoiceRepository] = None,
        case_service: Optional[CaseService] = None,
    ):
        self.repository = repository or InMemoryDataQualityRepository()
        self.invoice_repository = invoice_repository or InMemoryInvoiceRepository()
        self._case_service = case_service

    @property
    def case_service(self) -> CaseService:
        if self._case_service is None:
            self._case_service = get_case_service()
        return self._case_service

    def ingest_dataset(
        self,
        source: DataSource,
        dataset_type: str = "INVOICES",
        principal: Optional[AuthenticatedPrincipal] = None,
        correlation_id: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], DataQualityReport]:
        """
        Executes the standardized ingestion pipeline for a given data source.
        Enforces RBAC permission DATA_INGEST.
        """
        eff_principal = principal or get_internal_compatibility_principal()
        PermissionEvaluator.check_permission(eff_principal, PermissionEnum.DATA_INGEST)

        meta = source.metadata()
        ingestion_id = f"INGEST-{uuid.uuid4().hex[:8].upper()}"
        started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

        job_dict = {
            "ingestion_id": ingestion_id,
            "source_id": meta.source_id,
            "tenant_id": eff_principal.tenant_id,
            "dataset_type": dataset_type,
            "started_at": started_at,
            "completed_at": None,
            "status": "RUNNING",
            "total_records": 0,
            "accepted_records": 0,
            "rejected_records": 0,
            "duplicate_records": 0,
            "warning_records": 0,
            "quality_score": 0.0,
            "error_summary": [],
            "created_by": eff_principal.username,
            "correlation_id": correlation_id,
        }
        self.repository.save_ingestion_job(job_dict)

        # 1. Connect and Fetch Raw Records
        if not source.connect():
            job_dict["status"] = "FAILED"
            job_dict["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            job_dict["error_summary"] = [f"Failed to connect to data source '{meta.source_name}'."]
            self.repository.save_ingestion_job(job_dict)
            report = DataQualityReport(
                ingestion_id=ingestion_id,
                overall_quality_score=0.0,
                quality_status=QualityStatus.CRITICAL,
                dimension_scores={},
                total_records=0,
                accepted_records=0,
                rejected_records=0,
                duplicate_records=0,
                warning_records=0,
                issues=job_dict["error_summary"],
            )
            return job_dict, report

        raw_records = source.fetch_records()
        job_dict["total_records"] = len(raw_records)

        # Get existing fingerprints for deduplication
        existing_exact_fps, existing_potential_fps = self.repository.list_existing_fingerprints(tenant_id=eff_principal.tenant_id)

        record_results: List[RecordQualityResult] = []
        canonical_invoices: List[Invoice] = []

        for idx, raw in enumerate(raw_records, start=1):
            rec_id = f"REC-{ingestion_id}-{idx:04d}"

            # Step 1: Structural Validation
            struct_res = SchemaValidator.validate_structure(raw, record_index=idx)
            if not struct_res.is_valid:
                # Rejected Record
                q_res = DataQualityEngine.evaluate_record(
                    record_id=rec_id,
                    record_index=idx,
                    raw_record=raw,
                    canonical_invoice=None,
                    duplicate_status="UNIQUE",
                    structural_errors=struct_res.errors,
                    warnings=struct_res.warnings,
                )
                record_results.append(q_res)
                self.repository.save_record_result(
                    record=q_res,
                    ingestion_id=ingestion_id,
                    tenant_id=eff_principal.tenant_id,
                    raw_data=raw,
                    norm_data={},
                    fingerprint="",
                )
                continue

            # Step 2: Deterministic Normalization
            src_meta = SourceMetadata(
                source_type=meta.source_type.value,
                source_name=meta.source_name,
                source_file=meta.source_location,
                source_record_id=str(idx),
            )
            norm_res = InvoiceNormalizer.normalize_record(raw, record_index=idx, source_metadata=src_meta)

            if not norm_res.is_valid or norm_res.invoice is None:
                q_res = DataQualityEngine.evaluate_record(
                    record_id=rec_id,
                    record_index=idx,
                    raw_record=raw,
                    canonical_invoice=None,
                    duplicate_status="UNIQUE",
                    structural_errors=norm_res.errors,
                    warnings=norm_res.warnings,
                )
                record_results.append(q_res)
                self.repository.save_record_result(
                    record=q_res,
                    ingestion_id=ingestion_id,
                    tenant_id=eff_principal.tenant_id,
                    raw_data=raw,
                    norm_data={},
                    fingerprint="",
                )
                continue

            canon_inv: Invoice = norm_res.invoice

            # Step 3: Deduplication Fingerprinting
            dup_res = DeduplicationEngine.evaluate_record(
                supplier_gstin=canon_inv.seller_gstin or canon_inv.gstin,
                invoice_number=canon_inv.invoice_number,
                invoice_date=str(canon_inv.invoice_date),
                taxable_value=canon_inv.taxable_value,
                recipient_gstin=canon_inv.buyer_gstin or "",
                existing_exact_fps=existing_exact_fps,
                existing_potential_fps=existing_potential_fps,
            )

            # Record exact fingerprint into memory cache for this batch
            if dup_res.exact_fingerprint:
                existing_exact_fps[dup_res.exact_fingerprint] = canon_inv.invoice_id
            if dup_res.potential_fingerprint:
                existing_potential_fps[dup_res.potential_fingerprint] = canon_inv.invoice_id

            # Step 4: Data Quality Scoring
            q_res = DataQualityEngine.evaluate_record(
                record_id=rec_id,
                record_index=idx,
                raw_record=raw,
                canonical_invoice=canon_inv,
                duplicate_status=dup_res.status.value,
                structural_errors=[],
                warnings=norm_res.warnings,
                normalized_fields=[f"Field normalized to {k}={v}" for k, v in canon_inv.model_dump().items() if v is not None],
            )
            record_results.append(q_res)

            # Step 5: Data Lineage Creation
            lineage = LineageTracker.create_lineage(
                ingestion_id=ingestion_id,
                source_id=meta.source_id,
                source_record_id=str(idx),
                canonical_record_id=canon_inv.invoice_id,
                tenant_id=eff_principal.tenant_id,
                transformations=[
                    TransformationStep(
                        step_name="SCHEMA_VALIDATION",
                        input_value=raw,
                        output_value="VALID_STRUCTURE",
                        description="Record passed structural validation.",
                    ),
                    TransformationStep(
                        step_name="NORMALIZATION",
                        input_value=raw,
                        output_value=canon_inv.model_dump(),
                        description="Normalized raw string/numeric values into canonical Invoice.",
                    ),
                    TransformationStep(
                        step_name="DEDUPLICATION_CHECK",
                        input_value=dup_res.exact_fingerprint,
                        output_value=dup_res.status.value,
                        description=dup_res.description,
                    ),
                ],
            )

            # Step 6: Save Canonical Invoice & Lineage
            self.repository.save_record_result(
                record=q_res,
                ingestion_id=ingestion_id,
                tenant_id=eff_principal.tenant_id,
                raw_data=raw,
                norm_data=canon_inv.model_dump(),
                fingerprint=dup_res.exact_fingerprint,
            )
            self.repository.save_lineage_record(lineage)

            if q_res.status != "REJECTED" and q_res.status != "DUPLICATE":
                self.invoice_repository.save_invoice(canon_inv)
                canonical_invoices.append(canon_inv)

        # Aggregate Quality Report
        quality_report = DataQualityEngine.evaluate_batch(
            ingestion_id=ingestion_id,
            records=record_results,
        )
        self.repository.save_quality_report(quality_report)

        # Finalize Ingestion Job
        job_dict["completed_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        job_dict["accepted_records"] = quality_report.accepted_records
        job_dict["rejected_records"] = quality_report.rejected_records
        job_dict["duplicate_records"] = quality_report.duplicate_records
        job_dict["warning_records"] = quality_report.warning_records
        job_dict["quality_score"] = quality_report.overall_quality_score
        job_dict["error_summary"] = quality_report.issues

        if quality_report.rejected_records == job_dict["total_records"] and job_dict["total_records"] > 0:
            job_dict["status"] = "FAILED"
        elif quality_report.rejected_records > 0 or quality_report.warning_records > 0:
            job_dict["status"] = "COMPLETED_WITH_WARNINGS"
        else:
            job_dict["status"] = "COMPLETED"

        self.repository.save_ingestion_job(job_dict)

        logger.info(f"Completed ingestion '{ingestion_id}' for source '{meta.source_name}': Status={job_dict['status']}, Score={quality_report.overall_quality_score:.1f}")
        return job_dict, quality_report

    def get_ingestion_job(
        self, ingestion_id: str, principal: Optional[AuthenticatedPrincipal] = None
    ) -> Optional[Dict[str, Any]]:
        eff_principal = principal or get_internal_compatibility_principal()
        PermissionEvaluator.check_permission(eff_principal, PermissionEnum.DATA_READ)
        job = self.repository.get_ingestion_job(ingestion_id)
        if job and job.get("tenant_id") != eff_principal.tenant_id and not eff_principal.has_role("ADMIN"):
            raise ForbiddenException("Access denied to cross-tenant ingestion job.")
        return job

    def list_ingestion_jobs(
        self, principal: Optional[AuthenticatedPrincipal] = None, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        eff_principal = principal or get_internal_compatibility_principal()
        PermissionEvaluator.check_permission(eff_principal, PermissionEnum.DATA_READ)
        return self.repository.list_ingestion_jobs(tenant_id=eff_principal.tenant_id, status=status)

    list_jobs = list_ingestion_jobs

    def get_data_quality_report(
        self, ingestion_id: str, principal: Optional[AuthenticatedPrincipal] = None
    ) -> Optional[DataQualityReport]:
        eff_principal = principal or get_internal_compatibility_principal()
        PermissionEvaluator.check_permission(eff_principal, PermissionEnum.DATA_READ)
        return self.repository.get_quality_report(ingestion_id)

    def get_rejected_records(
        self, ingestion_id: str, principal: Optional[AuthenticatedPrincipal] = None
    ) -> List[RecordQualityResult]:
        eff_principal = principal or get_internal_compatibility_principal()
        PermissionEvaluator.check_permission(eff_principal, PermissionEnum.DATA_READ)
        all_recs = self.repository.list_records_for_job(ingestion_id)
        return [r for r in all_recs if r.status in ("REJECTED", "DUPLICATE")]

    def get_record_lineage(
        self, canonical_record_id: str, principal: Optional[AuthenticatedPrincipal] = None
    ) -> Optional[DataLineageRecord]:
        eff_principal = principal or get_internal_compatibility_principal()
        PermissionEvaluator.check_permission(eff_principal, PermissionEnum.DATA_READ)
        return self.repository.get_lineage_record(canonical_record_id)

    def trigger_intelligence_analysis(
        self,
        ingestion_id: str,
        create_case_for_critical: bool = True,
        principal: Optional[AuthenticatedPrincipal] = None,
    ) -> Dict[str, Any]:
        """
        Feeds canonical invoices from an ingestion job into existing GST Compliance & Risk engines.
        Optionally creates InvestigationCases for critical non-compliant invoices.
        """
        eff_principal = principal or get_internal_compatibility_principal()
        PermissionEvaluator.check_permission(eff_principal, PermissionEnum.DATA_VALIDATE)

        job = self.get_ingestion_job(ingestion_id, principal=eff_principal)
        if not job:
            raise ValueError(f"IngestionJob '{ingestion_id}' not found.")

        records = self.repository.list_records_for_job(ingestion_id)

        from app.agent.compliance_agent import GSTComplianceAgent
        agent = GSTComplianceAgent()

        invoices = []
        for rec in records:
            if rec.status in ("ACCEPTED", "ACCEPTED_WITH_WARNINGS", "POTENTIAL_DUPLICATE"):
                # Fetch record details if available
                details = getattr(self.repository, "_record_details", {}).get(rec.record_id, {})
                norm = details.get("norm_data", {})
                inv_no = norm.get("invoice_number") or norm.get("invoice_id")
                inv = self.invoice_repository.get_invoice(inv_no) if inv_no else None
                if not inv and norm:
                    from app.domain.models.invoice import Invoice
                    try:
                        inv = Invoice(**norm)
                    except Exception:
                        pass
                if not inv:
                    # Fallback to all invoices in repository matching record
                    all_invs = self.invoice_repository.list_all()
                    if all_invs:
                        inv = all_invs[0]  # Or match by index
                if inv:
                    invoices.append(inv)

        valid_invoices = invoices
        from app.engine.validation_engine import ValidationEngine
        from app.engine.decision_engine import DecisionEngine
        from app.rules.registry import create_default_registry
        from app.rules.context import ValidationContext

        registry = create_default_registry()
        context = ValidationContext()
        val_engine = ValidationEngine(registry_or_rules=registry, context=context)
        dec_engine = DecisionEngine()

        reports = []
        cases_created = []

        for inv in valid_invoices:
            val_report = val_engine.validate(inv)
            decision = dec_engine.decide(inv, val_report)
            reports.append(decision)

            risk_lvl = str(decision.risk_level or "").upper()
            status_val = str(decision.status or "").upper()

            if create_case_for_critical and (risk_lvl in ("HIGH", "CRITICAL") or status_val == "NON_COMPLIANT"):
                case = self.case_service.create_case(
                    title=f"GST Compliance Investigation: {inv.invoice_number}",
                    description=f"Auto-generated case from ingestion '{ingestion_id}'. Gate failure: {decision.justification}",
                    invoice_id=inv.invoice_number,
                    counterparty_gstin=inv.gstin,
                    source="AUTOMATED_INGESTION_SCAN",
                    principal=eff_principal,
                )
                cases_created.append(case.case_id)

                # Link lineage
                lineage = self.repository.get_lineage_record(inv.invoice_id)
                if lineage:
                    LineageTracker.link_downstream_case(lineage, case_id=case.case_id)
                    self.repository.save_lineage_record(lineage)

        return {
            "ingestion_id": ingestion_id,
            "total_analyzed": len(valid_invoices),
            "cases_created": len(cases_created),
            "critical_issues_found": len(cases_created),
            "created_case_ids": cases_created,
            "decisions": [d.to_dict() for d in reports],
        }
