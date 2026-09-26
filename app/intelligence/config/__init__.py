"""
app.intelligence.config
=======================
Configuration loader and schemas for Duplicate & Anomaly Intelligence.
"""

from app.intelligence.config.intelligence_config import (
    IntelligenceConfig,
    DuplicatePolicyConfig,
    AnomalyPolicyConfig,
    default_intelligence_config,
)

__all__ = [
    "IntelligenceConfig",
    "DuplicatePolicyConfig",
    "AnomalyPolicyConfig",
    "default_intelligence_config",
]
