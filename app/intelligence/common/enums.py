"""
app.intelligence.common.enums
=============================
Enumerations for Duplicate & Anomaly Intelligence (Sprint 7).
Enforces unambiguous, explainable categorization without conflating with fraud or non-compliance.
"""

from enum import Enum


class IntelligenceCategory(str, Enum):
    """Broad category of intelligence finding."""
    DUPLICATE = "DUPLICATE"
    ANOMALY = "ANOMALY"


class DuplicateMatchType(str, Enum):
    """Categorization of duplicate candidate match strength."""
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    HIGH_CONFIDENCE_NEAR_DUPLICATE = "HIGH_CONFIDENCE_NEAR_DUPLICATE"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    NO_DUPLICATE = "NO_DUPLICATE"
    NOT_EVALUATED = "NOT_EVALUATED"


class AnomalyDimension(str, Enum):
    """Behavioral dimension along which an anomaly was detected."""
    VALUE_ANOMALY = "VALUE_ANOMALY"
    TAX_RATE_ANOMALY = "TAX_RATE_ANOMALY"
    FREQUENCY_ANOMALY = "FREQUENCY_ANOMALY"
    TIMING_ANOMALY = "TIMING_ANOMALY"


class AnomalyStatus(str, Enum):
    """Statistical evaluation status of a transaction."""
    NORMAL = "NORMAL"
    ANOMALOUS = "ANOMALOUS"
    INSUFFICIENT_BASELINE = "INSUFFICIENT_BASELINE"
    NOT_EVALUATED = "NOT_EVALUATED"


class AnomalyLevel(str, Enum):
    """Severity classification of anomaly signal."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IntelligenceConfidence(str, Enum):
    """Confidence level in the validity and reliability of the intelligence signal."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
