"""
app.intelligence.config.intelligence_config
===========================================
Typed configuration loader for Duplicate & Anomaly Intelligence (Sprint 7).
Loads YAML configuration from config/intelligence/ with robust code defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import yaml

from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "config",
    "intelligence",
)


# =====================================================================
# Duplicate Policy Configuration Models
# =====================================================================

class DuplicateNormalizationConfig(BaseModel):
    strip_whitespace: bool = True
    uppercase: bool = True
    remove_separators: bool = True


class DuplicateWeightsConfig(BaseModel):
    supplier_gstin_match: float = 30.0
    buyer_gstin_match: float = 15.0
    invoice_number_similarity: float = 25.0
    date_proximity: float = 15.0
    taxable_value_similarity: float = 10.0
    tax_amount_similarity: float = 5.0


class DuplicateThresholdsConfig(BaseModel):
    exact_match: float = 100.0
    high_confidence_near: float = 85.0
    possible_duplicate: float = 65.0


class DuplicateDateBracketsConfig(BaseModel):
    same_day: int = 0
    tight_days: int = 3
    moderate_days: int = 7
    loose_days: int = 30


class DuplicateAmountToleranceConfig(BaseModel):
    exact: float = 0.0
    tight: float = 1.0
    moderate: float = 5.0


class DuplicateRecurringProtectionConfig(BaseModel):
    enabled: bool = True
    min_days_separation: int = 25
    max_days_separation: int = 35
    number_similarity_ceiling: float = 0.85


class DuplicatePolicyConfig(BaseModel):
    version: str = "1.0"
    normalization: DuplicateNormalizationConfig = Field(default_factory=DuplicateNormalizationConfig)
    weights: DuplicateWeightsConfig = Field(default_factory=DuplicateWeightsConfig)
    thresholds: DuplicateThresholdsConfig = Field(default_factory=DuplicateThresholdsConfig)
    date_proximity_brackets: DuplicateDateBracketsConfig = Field(default_factory=DuplicateDateBracketsConfig)
    amount_tolerance_pct: DuplicateAmountToleranceConfig = Field(default_factory=DuplicateAmountToleranceConfig)
    recurring_protection: DuplicateRecurringProtectionConfig = Field(default_factory=DuplicateRecurringProtectionConfig)


# =====================================================================
# Anomaly Policy Configuration Models
# =====================================================================

class AnomalyIqrConfig(BaseModel):
    outlier_multiplier: float = 1.5
    extreme_multiplier: float = 3.0


class AnomalyRobustZConfig(BaseModel):
    threshold_medium: float = 2.5
    threshold_high: float = 3.5
    threshold_critical: float = 5.0


class AnomalyTaxRateConfig(BaseModel):
    statutory_rates: List[float] = [0.0, 5.0, 12.0, 18.0, 28.0]
    tolerance_pct: float = 0.5


class AnomalyFrequencyConfig(BaseModel):
    window_days: int = 7
    burst_multiplier: float = 3.0


class AnomalyPolicyConfig(BaseModel):
    version: str = "1.0"
    baseline_hierarchy: List[str] = ["COUNTERPARTY", "HSN", "PORTFOLIO"]
    minimum_observations: Dict[str, int] = {"counterparty": 3, "hsn": 5, "portfolio": 10}
    statistical_method: str = "ROBUST_Z_SCORE_AND_IQR"
    iqr: AnomalyIqrConfig = Field(default_factory=AnomalyIqrConfig)
    robust_z: AnomalyRobustZConfig = Field(default_factory=AnomalyRobustZConfig)
    tax_rate: AnomalyTaxRateConfig = Field(default_factory=AnomalyTaxRateConfig)
    frequency: AnomalyFrequencyConfig = Field(default_factory=AnomalyFrequencyConfig)


# =====================================================================
# Unified Intelligence Configuration Loader
# =====================================================================

class IntelligenceConfig(BaseModel):
    duplicate: DuplicatePolicyConfig = Field(default_factory=DuplicatePolicyConfig)
    anomaly: AnomalyPolicyConfig = Field(default_factory=AnomalyPolicyConfig)

    @classmethod
    def load_from_dir(cls, config_dir: Optional[str] = None) -> IntelligenceConfig:
        """Load configuration from YAML files in config_dir, falling back to code defaults."""
        target_dir = config_dir or DEFAULT_CONFIG_DIR
        dup_path = os.path.join(target_dir, "duplicate_policy.yaml")
        anom_path = os.path.join(target_dir, "anomaly_policy.yaml")

        dup_cfg = DuplicatePolicyConfig()
        if os.path.exists(dup_path):
            try:
                with open(dup_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    raw_dup = data.get("duplicate_policy", data)
                    dup_cfg = DuplicatePolicyConfig(**raw_dup)
            except Exception as e:
                logger.warning(f"Failed to parse duplicate_policy.yaml from {dup_path}: {e}. Using defaults.")

        anom_cfg = AnomalyPolicyConfig()
        if os.path.exists(anom_path):
            try:
                with open(anom_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                    raw_anom = data.get("anomaly_policy", data)
                    anom_cfg = AnomalyPolicyConfig(**raw_anom)
            except Exception as e:
                logger.warning(f"Failed to parse anomaly_policy.yaml from {anom_path}: {e}. Using defaults.")

        return cls(duplicate=dup_cfg, anomaly=anom_cfg)


# Module-level default configuration instance
default_intelligence_config = IntelligenceConfig.load_from_dir()
