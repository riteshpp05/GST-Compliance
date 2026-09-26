"""
app.investigation.config.investigation_config
=============================================
Typed configuration loader for Root Cause & Blast Radius Intelligence (Sprint 8 + 9).
Loads YAML configuration from config/investigation/ with robust code defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import yaml

from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "config",
    "investigation",
)


# =====================================================================
# Root Cause Policy Configuration
# =====================================================================

class RootCauseWeightsConfig(BaseModel):
    evidence_strength: float = 30.0
    pattern_recurrence: float = 20.0
    population_coverage: float = 20.0
    temporal_consistency: float = 10.0
    counterparty_concentration: float = 10.0
    rule_concentration: float = 10.0


class RootCauseConfidenceConfig(BaseModel):
    high: float = 75.0
    medium: float = 50.0
    low: float = 30.0
    min_population_size: int = 2
    min_independent_sources_for_high: int = 2


class RootCauseLikelihoodConfig(BaseModel):
    high: float = 70.0
    medium: float = 45.0
    low: float = 20.0


class ConcentrationThresholdsConfig(BaseModel):
    counterparty_high: float = 0.50
    rule_high: float = 0.60
    hsn_high: float = 0.50
    state_high: float = 0.60


class PatternThresholdsConfig(BaseModel):
    min_rule_recurrence: int = 2
    min_counterparty_invoices: int = 2
    min_period_recurrence: int = 2


class RootCausePolicyConfig(BaseModel):
    version: str = "1.0"
    weights: RootCauseWeightsConfig = Field(default_factory=RootCauseWeightsConfig)
    confidence_thresholds: RootCauseConfidenceConfig = Field(default_factory=RootCauseConfidenceConfig)
    likelihood_thresholds: RootCauseLikelihoodConfig = Field(default_factory=RootCauseLikelihoodConfig)
    concentration_thresholds: ConcentrationThresholdsConfig = Field(default_factory=ConcentrationThresholdsConfig)
    pattern_thresholds: PatternThresholdsConfig = Field(default_factory=PatternThresholdsConfig)


# =====================================================================
# Blast Radius Policy Configuration
# =====================================================================

class TrendAnalysisConfig(BaseModel):
    min_periods_required: int = 2
    expansion_threshold_pct: float = 15.0
    contraction_threshold_pct: float = -15.0
    sudden_onset_ratio: float = 0.50
    stability_tolerance_pct: float = 10.0


class SystemicClassificationConfig(BaseModel):
    min_population_for_systemic: int = 3
    isolated_max_invoices: int = 2
    isolated_max_counterparties: int = 1
    isolated_max_ratio: float = 0.05
    concentrated_share_threshold: float = 0.60
    systemic_min_counterparties: int = 3
    systemic_min_periods: int = 2
    systemic_min_ratio: float = 0.15


class DimensionLimitsConfig(BaseModel):
    top_counterparties: int = 10
    top_rules: int = 10
    top_periods: int = 12
    top_hsns: int = 10
    top_states: int = 10


class BlastRadiusPolicyConfig(BaseModel):
    version: str = "1.0"
    trend_analysis: TrendAnalysisConfig = Field(default_factory=TrendAnalysisConfig)
    classification: SystemicClassificationConfig = Field(default_factory=SystemicClassificationConfig)
    dimension_limits: DimensionLimitsConfig = Field(default_factory=DimensionLimitsConfig)


# =====================================================================
# Combined Investigation Config
# =====================================================================

class InvestigationConfig(BaseModel):
    root_cause: RootCausePolicyConfig = Field(default_factory=RootCausePolicyConfig)
    blast_radius: BlastRadiusPolicyConfig = Field(default_factory=BlastRadiusPolicyConfig)


def load_investigation_config(config_dir: Optional[str] = None) -> InvestigationConfig:
    """
    Load investigation policies from YAML files with fallback to code defaults.
    """
    target_dir = Path(config_dir or DEFAULT_CONFIG_DIR)

    # 1. Load Root Cause Policy
    rc_config = RootCausePolicyConfig()
    rc_path = target_dir / "root_cause_policy.yaml"
    if rc_path.exists():
        try:
            with open(rc_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and "root_cause_policy" in data:
                    rc_config = RootCausePolicyConfig(**data["root_cause_policy"])
                    logger.info(f"Loaded root cause policy from {rc_path}")
        except Exception as e:
            logger.warning(f"Failed to load {rc_path}, using defaults: {e}")

    # 2. Load Blast Radius Policy
    br_config = BlastRadiusPolicyConfig()
    br_path = target_dir / "blast_radius_policy.yaml"
    if br_path.exists():
        try:
            with open(br_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and "blast_radius_policy" in data:
                    br_config = BlastRadiusPolicyConfig(**data["blast_radius_policy"])
                    logger.info(f"Loaded blast radius policy from {br_path}")
        except Exception as e:
            logger.warning(f"Failed to load {br_path}, using defaults: {e}")

    return InvestigationConfig(root_cause=rc_config, blast_radius=br_config)


default_investigation_config = load_investigation_config()
