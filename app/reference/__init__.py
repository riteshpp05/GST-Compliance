"""
UC15 GST Compliance Agent — Reference Intelligence Domain (Sprint 4)
Provides version-aware, effective-date bounded statutory master reference services.
"""
from app.reference.models.base import BaseReferenceRecord
from app.reference.models.ewb_policy import EWBPolicyReference
from app.reference.models.hsn import HSNReference
from app.reference.models.itc_policy import ITCPolicyReference
from app.reference.models.snapshot import ReferenceSnapshot
from app.reference.models.state import StateReference
from app.reference.models.tax_rate import TaxRateReference
from app.reference.repositories.base import BaseReferenceRepository
from app.reference.repositories.in_memory import InMemoryReferenceRepository
from app.reference.resolvers.effective_date import (
    EffectiveDateResolver,
    ResolutionResult,
    ResolutionStatus,
)
from app.reference.services.reference_service import ReferenceService

__all__ = [
    "BaseReferenceRecord",
    "HSNReference",
    "TaxRateReference",
    "StateReference",
    "EWBPolicyReference",
    "ITCPolicyReference",
    "ReferenceSnapshot",
    "ResolutionStatus",
    "ResolutionResult",
    "EffectiveDateResolver",
    "BaseReferenceRepository",
    "InMemoryReferenceRepository",
    "ReferenceService",
]
