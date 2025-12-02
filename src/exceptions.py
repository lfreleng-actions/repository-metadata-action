# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Custom exceptions for the repository metadata action.
"""


class MetadataExtractionError(Exception):
    """Base exception for metadata extraction errors."""


class ConfigurationError(MetadataExtractionError):
    """Raised when configuration is invalid or missing."""


class GitOperationError(MetadataExtractionError):
    """Raised when git operations fail."""


class GitHubAPIError(MetadataExtractionError):
    """Raised when GitHub API operations fail."""


class ValidationError(MetadataExtractionError):
    """Raised when data validation fails."""


class OutputError(MetadataExtractionError):
    """Raised when output generation or writing fails."""
