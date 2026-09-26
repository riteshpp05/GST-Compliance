"""
UC15 GST Compliance Agent — Risk Engine Configuration
Typed configuration loader for Risk Levels, Weights, and Policies.
Loads from YAML configuration files in config/risk/ with robust code defaults.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import yaml

from app.infrastructure.logging import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config", "risk")


class RiskLevelRange(BaseModel):
    min: float
    max: float
    label: str = ""
    description: str = ""


class RiskSeverityWeights(BaseModel):
    INFO: float = 0.0
    LOW: float = 5.0
    MEDIUM: float = 15.0
    HIGH: float = 25.0
    CRITICAL: float = 40.0


class RiskCategoryWeights(BaseModel):
    MASTER_DATA: float = 5.0
    CLASSIFICATION: float = 10.0
    TAX: float = 20.0
    PLACE_OF_SUPPLY: float = 15.0
    EWAY_BILL: float = 10.0
    ITC: float = 20.0
    DATA_QUALITY: float = 5.0
    OTHER: float = 5.0


class RiskWeightConfig(BaseModel):
    severity: RiskSeverityWeights = Field(default_factory=RiskSeverityWeights)
    category: RiskCategoryWeights = Field(default_factory=RiskCategoryWeights)
    multiple_findings_penalty: float = 10.0
    max_multiple_findings_penalty: float = 30.0
    warning_severity_factor: float = 0.5
    data_quality_penalty: float = 5.0
    max_data_quality_penalty: float = 15.0


class CriticalOverrideConfig(BaseModel):
    enabled: bool = True
    min_score_floor: float = 80.0
    min_risk_level: str = "CRITICAL"
    force_priority: str = "P1"


class ConfidencePenalties(BaseModel):
    missing_hsn_master: float = 0.20
    unmatched_gstr2b: float = 0.15
    data_quality_failure: float = 0.10
    missing_state_ref: float = 0.10


class ConfidenceConfig(BaseModel):
    high_threshold: float = 0.90
    medium_threshold: float = 0.70
    penalties: ConfidencePenalties = Field(default_factory=ConfidencePenalties)


class RiskPolicyConfig(BaseModel):
    model_version: str = "1.0"
    priority_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "CRITICAL": "P1",
            "HIGH": "P2",
            "MEDIUM": "P3",
            "MODERATE": "P4",
            "LOW": "P4",
        }
    )
    critical_override: CriticalOverrideConfig = Field(default_factory=CriticalOverrideConfig)
    confidence: ConfidenceConfig = Field(default_factory=ConfidenceConfig)


class RiskConfig(BaseModel):
    levels: Dict[str, RiskLevelRange] = Field(
        default_factory=lambda: {
            "LOW": RiskLevelRange(min=0.0, max=19.99, label="Low Risk"),
            "MODERATE": RiskLevelRange(min=20.0, max=39.99, label="Moderate Risk"),
            "MEDIUM": RiskLevelRange(min=40.0, max=59.99, label="Medium Risk"),
            "HIGH": RiskLevelRange(min=60.0, max=79.99, label="High Risk"),
            "CRITICAL": RiskLevelRange(min=80.0, max=100.0, label="Critical Risk"),
        }
    )
    weights: RiskWeightConfig = Field(default_factory=RiskWeightConfig)
    policy: RiskPolicyConfig = Field(default_factory=RiskPolicyConfig)


def _load_yaml(file_path: str) -> Optional[Dict[str, Any]]:
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.warning(f"Failed to load YAML from {file_path}: {e}")
        return None


def load_risk_config(config_dir: Optional[str] = None) -> RiskConfig:
    """Load risk configuration from external YAML files with fallback to code defaults."""
    dir_path = config_dir or DEFAULT_CONFIG_DIR
    
    # 1. Load Levels
    levels_data = _load_yaml(os.path.join(dir_path, "risk_levels.yaml"))
    levels_dict = {}
    if levels_data and "risk_levels" in levels_data:
        for k, v in levels_data["risk_levels"].items():
            levels_dict[k] = RiskLevelRange(**v)
    
    # 2. Load Weights
    weights_data = _load_yaml(os.path.join(dir_path, "risk_weights.yaml"))
    weights_obj = None
    if weights_data and "risk_weights" in weights_data:
        weights_obj = RiskWeightConfig(**weights_data["risk_weights"])

    # 3. Load Policy
    policy_data = _load_yaml(os.path.join(dir_path, "risk_policy.yaml"))
    policy_obj = None
    if policy_data and "risk_policy" in policy_data:
        policy_obj = RiskPolicyConfig(**policy_data["risk_policy"])

    return RiskConfig(
        levels=levels_dict if levels_dict else RiskConfig().levels,
        weights=weights_obj if weights_obj else RiskWeightConfig(),
        policy=policy_obj if policy_obj else RiskPolicyConfig(),
    )
