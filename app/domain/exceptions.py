"""
UC15 GST Compliance Agent — Domain Exceptions
"""
from __future__ import annotations
from typing import Optional


class UC15Exception(Exception):
    """Base exception for all UC15 errors."""
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class DataLoadError(UC15Exception):
    """Raised when data loading fails."""


class NormalizationError(UC15Exception):
    """Raised when data normalization fails."""


class ValidationError(UC15Exception):
    """Raised when validation execution fails."""


class ConfigurationError(UC15Exception):
    """Raised when configuration is missing or invalid."""


class RuleExecutionError(UC15Exception):
    """Raised when a specific compliance rule execution encounters an unhandled error."""


class InvoiceNotFoundError(UC15Exception):
    """Raised when a queried invoice is not found in the repository."""
