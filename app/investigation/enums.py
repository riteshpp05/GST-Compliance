"""
app.investigation.enums
=======================
Taxonomy and controlled enumerations for Root Cause & Blast Radius Intelligence (Sprint 8 + 9).
Provides strictly typed, audit-safe categorizations across evidence, root cause hypotheses,
systemic impact levels, and temporal trends.
"""

from __future__ import annotations
from enum import Enum


class RootCauseType(str, Enum):
    """
    Controlled taxonomy of root cause hypotheses.
    Root causes represent the underlying systemic or operational reason for compliance discrepancies,
    as distinguished from mere symptoms (e.g. failing validation gates).
    """
    MASTER_DATA = "MASTER_DATA"
    TAX_CONFIGURATION = "TAX_CONFIGURATION"
    GSTIN_CONFIGURATION = "GSTIN_CONFIGURATION"
    HSN_CLASSIFICATION = "HSN_CLASSIFICATION"
    TAX_RATE_CONFIGURATION = "TAX_RATE_CONFIGURATION"
    PLACE_OF_SUPPLY = "PLACE_OF_SUPPLY"
    ITC_PROCESS = "ITC_PROCESS"
    EWB_PROCESS = "EWB_PROCESS"
    DATA_QUALITY = "DATA_QUALITY"
    DUPLICATE_PROCESS = "DUPLICATE_PROCESS"
    INVOICE_CAPTURE = "INVOICE_CAPTURE"
    INTEGRATION_SYNC = "INTEGRATION_SYNC"
    PROCESS_TIMING = "PROCESS_TIMING"
    REFERENCE_DATA = "REFERENCE_DATA"
    UNKNOWN = "UNKNOWN"


class RootCauseStatus(str, Enum):
    """Lifecycle and confirmation state of an identified root cause."""
    ACTIVE = "ACTIVE"
    CONFIRMED = "CONFIRMED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class RootCauseConfidence(str, Enum):
    """
    Confidence rating for root cause identification.
    HIGH: Multiple independent evidence sources agree across population.
    MEDIUM: Strong pattern with limited independent verification.
    LOW: Weak pattern or small sample size.
    INSUFFICIENT_EVIDENCE: Not enough verifiable evidence to establish hypothesis.
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class RootCauseLikelihood(str, Enum):
    """Likelihood of a candidate root cause explaining the observed discrepancy."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class EvidenceType(str, Enum):
    """Controlled taxonomy of evidence types supporting root-cause hypotheses."""
    RULE_FAILURE_PATTERN = "RULE_FAILURE_PATTERN"
    HISTORICAL_PATTERN = "HISTORICAL_PATTERN"
    COUNTERPARTY_PATTERN = "COUNTERPARTY_PATTERN"
    DUPLICATE_PATTERN = "DUPLICATE_PATTERN"
    ANOMALY_PATTERN = "ANOMALY_PATTERN"
    DATA_QUALITY_PATTERN = "DATA_QUALITY_PATTERN"
    REFERENCE_CHANGE = "REFERENCE_CHANGE"
    FINANCIAL_PATTERN = "FINANCIAL_PATTERN"
    TEMPORAL_PATTERN = "TEMPORAL_PATTERN"
    GEOGRAPHIC_PATTERN = "GEOGRAPHIC_PATTERN"


class TrendClassification(str, Enum):
    """Deterministic classification of temporal growth or containment of an issue."""
    EXPANDING = "EXPANDING"
    CONTRACTING = "CONTRACTING"
    STABLE = "STABLE"
    SUDDEN_ONSET = "SUDDEN_ONSET"
    RECOVERING = "RECOVERING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class SystemicClassification(str, Enum):
    """
    Deterministic classification of the organizational and operational scope.
    ISOLATED: Single invoice or low-exposure one-off anomaly.
    CONCENTRATED: Issue highly focused in specific counterparty, rule, or state.
    SYSTEMIC: Broad issue spanning multiple counterparties, periods, or rules.
    EMERGING_SYSTEMIC: Rapidly growing pattern trending toward systemic breach.
    INSUFFICIENT_DATA: Insufficient sample size to make boundary classification.
    """
    ISOLATED = "ISOLATED"
    CONCENTRATED = "CONCENTRATED"
    SYSTEMIC = "SYSTEMIC"
    EMERGING_SYSTEMIC = "EMERGING_SYSTEMIC"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class InvestigationStatus(str, Enum):
    """Lifecycle status of an end-to-end investigation case."""
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
