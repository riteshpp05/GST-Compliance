"""
app.data.quality.quality_engine
===============================
Dedicated Data Quality Engine for UC15 (Sprint 17).
Evaluates GST datasets across 6 dimensions and computes deterministic quality scores.

CRITICAL RULE:
ACCURACY and TIMELINESS are quality indicator heuristics, NOT absolute real-world factual guarantees.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from app.domain.models.invoice import Invoice


class QualityDimensionEnum(str, Enum):
    """The 6 fundamental data quality dimensions."""
    COMPLETENESS = "COMPLETENESS"
    VALIDITY = "VALIDITY"
    CONSISTENCY = "CONSISTENCY"
    UNIQUENESS = "UNIQUENESS"
    ACCURACY = "ACCURACY"      # Quality indicator heuristic (master alignment)
    TIMELINESS = "TIMELINESS"  # Quality indicator heuristic (filing period proximity)


class QualityStatus(str, Enum):
    """Overall Data Quality Status Classification."""
    EXCELLENT = "EXCELLENT"    # >= 95.0
    GOOD = "GOOD"              # >= 85.0
    ACCEPTABLE = "ACCEPTABLE"  # >= 75.0
    POOR = "POOR"              # >= 60.0
    CRITICAL = "CRITICAL"      # < 60.0


@dataclass
class RecordQualityResult:
    """Quality evaluation result for an individual canonical GST record."""
    record_id: str
    record_index: int
    quality_score: float
    status: str  # ACCEPTED | ACCEPTED_WITH_WARNINGS | REJECTED | DUPLICATE | POTENTIAL_DUPLICATE
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    normalized_fields: List[str] = field(default_factory=list)
    duplicate_status: str = "UNIQUE"
    validation_status: str = "VALID"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "record_index": self.record_index,
            "quality_score": round(self.quality_score, 2),
            "status": self.status,
            "dimension_scores": {k: round(v, 2) for k, v in self.dimension_scores.items()},
            "errors": self.errors,
            "warnings": self.warnings,
            "normalized_fields": self.normalized_fields,
            "duplicate_status": self.duplicate_status,
            "validation_status": self.validation_status,
        }


@dataclass
class DataQualityReport:
    """Aggregated batch data quality report for an ingestion job."""
    ingestion_id: str
    overall_quality_score: float
    quality_status: QualityStatus
    dimension_scores: Dict[str, float]
    total_records: int
    accepted_records: int
    rejected_records: int
    duplicate_records: int
    warning_records: int
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ingestion_id": self.ingestion_id,
            "overall_quality_score": round(self.overall_quality_score, 2),
            "quality_status": self.quality_status.value,
            "dimension_scores": {k: round(v, 2) for k, v in self.dimension_scores.items()},
            "total_records": self.total_records,
            "accepted_records": self.accepted_records,
            "rejected_records": self.rejected_records,
            "duplicate_records": self.duplicate_records,
            "warning_records": self.warning_records,
            "issues": self.issues,
            "warnings": self.warnings,
            "created_at": self.created_at,
        }


class DataQualityEngine:
    """
    Evaluates raw and canonical GST records across 6 quality dimensions:
    - COMPLETENESS (weight 25%)
    - VALIDITY (weight 25%)
    - CONSISTENCY (weight 20%)
    - UNIQUENESS (weight 15%)
    - ACCURACY [Indicator Heuristic] (weight 10%)
    - TIMELINESS [Indicator Heuristic] (weight 5%)
    """

    DIMENSION_WEIGHTS: Dict[QualityDimensionEnum, float] = {
        QualityDimensionEnum.COMPLETENESS: 0.25,
        QualityDimensionEnum.VALIDITY: 0.25,
        QualityDimensionEnum.CONSISTENCY: 0.20,
        QualityDimensionEnum.UNIQUENESS: 0.15,
        QualityDimensionEnum.ACCURACY: 0.10,
        QualityDimensionEnum.TIMELINESS: 0.05,
    }

    @classmethod
    def evaluate_record(
        cls,
        record_id: str,
        record_index: int,
        raw_record: Dict[str, Any],
        canonical_invoice: Optional[Invoice],
        duplicate_status: str = "UNIQUE",
        structural_errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        normalized_fields: Optional[List[str]] = None,
    ) -> RecordQualityResult:
        errs = list(structural_errors or [])
        warns = list(warnings or [])
        norm_fields = list(normalized_fields or [])

        # 1. COMPLETENESS (25%)
        # Check presence of mandatory fields
        mandatory_keys = ["invoice_number", "invoice_date", "gstin", "place_of_supply", "hsn_sac", "taxable_value"]
        present_count = 0
        if canonical_invoice:
            inv_dict = canonical_invoice.model_dump()
            for k in mandatory_keys:
                v = inv_dict.get(k)
                if v is not None and str(v).strip() != "":
                    present_count += 1
            completeness = (present_count / len(mandatory_keys)) * 100.0
        else:
            completeness = 0.0

        # 2. VALIDITY (25%)
        if not canonical_invoice or len(errs) > 0:
            validity = 0.0 if not canonical_invoice else max(0.0, 100.0 - (len(errs) * 30.0))
        else:
            # Format checks
            val_score = 100.0
            if len(canonical_invoice.gstin) != 15:
                val_score -= 20.0
            validity = max(0.0, val_score)

        # 3. CONSISTENCY (20%)
        if canonical_invoice:
            calc_tax = canonical_invoice.total_tax
            calc_amt = canonical_invoice.taxable_value + calc_tax
            diff = abs(calc_amt - canonical_invoice.total_amount)
            consistency = 100.0 if diff < Decimal("1.00") else max(0.0, 100.0 - float(diff))
        else:
            consistency = 0.0

        # 4. UNIQUENESS (15%)
        if duplicate_status == "EXACT_DUPLICATE":
            uniqueness = 0.0
            warns.append("Record is an exact duplicate of a previously ingested record.")
        elif duplicate_status == "POTENTIAL_DUPLICATE":
            uniqueness = 50.0
            warns.append("Record flagged as potential duplicate (review signal).")
        else:
            uniqueness = 100.0

        # 5. ACCURACY Indicator Heuristic (10%)
        # Heuristic alignment with standard state/HSN rules
        accuracy = 100.0 if canonical_invoice and canonical_invoice.hsn_sac else 50.0

        # 6. TIMELINESS Indicator Heuristic (5%)
        # Heuristic proximity of invoice date
        timeliness = 100.0
        if canonical_invoice:
            try:
                inv_dt_str = str(canonical_invoice.invoice_date)
                inv_dt = datetime.date.fromisoformat(inv_dt_str)
                age_days = (datetime.date.today() - inv_dt).days
                if age_days > 365:
                    timeliness = 60.0
                    warns.append(f"Invoice date {inv_dt_str} is older than 1 year.")
            except (ValueError, TypeError):
                timeliness = 50.0

        dim_scores = {
            QualityDimensionEnum.COMPLETENESS.value: completeness,
            QualityDimensionEnum.VALIDITY.value: validity,
            QualityDimensionEnum.CONSISTENCY.value: consistency,
            QualityDimensionEnum.UNIQUENESS.value: uniqueness,
            QualityDimensionEnum.ACCURACY.value: accuracy,
            QualityDimensionEnum.TIMELINESS.value: timeliness,
        }

        # Weighted Score
        record_score = sum(
            dim_scores[dim.value] * weight
            for dim, weight in cls.DIMENSION_WEIGHTS.items()
        )

        # Status determination
        if not canonical_invoice or len(errs) > 0:
            rec_status = "REJECTED"
        elif duplicate_status == "EXACT_DUPLICATE":
            rec_status = "DUPLICATE"
        elif duplicate_status == "POTENTIAL_DUPLICATE":
            rec_status = "POTENTIAL_DUPLICATE"
        elif len(warns) > 0:
            rec_status = "ACCEPTED_WITH_WARNINGS"
        else:
            rec_status = "ACCEPTED"

        return RecordQualityResult(
            record_id=record_id,
            record_index=record_index,
            quality_score=record_score,
            status=rec_status,
            dimension_scores=dim_scores,
            errors=errs,
            warnings=warns,
            normalized_fields=norm_fields,
            duplicate_status=duplicate_status,
            validation_status="INVALID" if len(errs) > 0 else "VALID",
        )

    @classmethod
    def evaluate_batch(
        cls,
        ingestion_id: str,
        records: List[RecordQualityResult],
    ) -> DataQualityReport:
        if not records:
            return DataQualityReport(
                ingestion_id=ingestion_id,
                overall_quality_score=0.0,
                quality_status=QualityStatus.CRITICAL,
                dimension_scores={d.value: 0.0 for d in QualityDimensionEnum},
                total_records=0,
                accepted_records=0,
                rejected_records=0,
                duplicate_records=0,
                warning_records=0,
                issues=["Empty dataset provided."],
            )

        total = len(records)
        accepted = sum(1 for r in records if r.status in ("ACCEPTED", "ACCEPTED_WITH_WARNINGS", "POTENTIAL_DUPLICATE"))
        rejected = sum(1 for r in records if r.status == "REJECTED")
        duplicates = sum(1 for r in records if r.status == "DUPLICATE")
        warnings = sum(1 for r in records if r.status in ("ACCEPTED_WITH_WARNINGS", "POTENTIAL_DUPLICATE"))

        # Average dimension scores across records
        avg_dim_scores: Dict[str, float] = {}
        for dim in QualityDimensionEnum:
            scores = [r.dimension_scores.get(dim.value, 0.0) for r in records]
            avg_dim_scores[dim.value] = sum(scores) / total if total else 0.0

        overall_score = sum(
            avg_dim_scores[dim.value] * weight
            for dim, weight in cls.DIMENSION_WEIGHTS.items()
        )

        if overall_score >= 95.0:
            status = QualityStatus.EXCELLENT
        elif overall_score >= 85.0:
            status = QualityStatus.GOOD
        elif overall_score >= 75.0:
            status = QualityStatus.ACCEPTABLE
        elif overall_score >= 60.0:
            status = QualityStatus.POOR
        else:
            status = QualityStatus.CRITICAL

        issues: List[str] = []
        all_warnings: List[str] = []

        if rejected > 0:
            issues.append(f"{rejected}/{total} records were rejected due to structural or validation errors.")
        if duplicates > 0:
            issues.append(f"{duplicates}/{total} records were exact duplicates.")

        pot_dups = sum(1 for r in records if r.duplicate_status == "POTENTIAL_DUPLICATE")
        if pot_dups > 0:
            all_warnings.append(f"{pot_dups} records flagged as potential duplicates for review.")

        return DataQualityReport(
            ingestion_id=ingestion_id,
            overall_quality_score=overall_score,
            quality_status=status,
            dimension_scores=avg_dim_scores,
            total_records=total,
            accepted_records=accepted,
            rejected_records=rejected,
            duplicate_records=duplicates,
            warning_records=warnings,
            issues=issues,
            warnings=all_warnings,
        )
