# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Constants used throughout the repository metadata action.
Centralizes magic numbers and configuration values for maintainability.
"""

# GitHub API limits
MAX_PR_FILES = 3000  # Maximum number of files GitHub API returns per PR

# Git operation defaults
DEFAULT_GIT_FETCH_DEPTH = 15  # Default depth for git fetch --deepen in shallow clones

# Cache configuration
MERGE_BASE_CACHE_ENABLED = True  # Whether to cache merge base calculations

# String truncation limits
MAX_OUTPUT_STRING_LENGTH = 10_000  # Maximum length for sanitized output strings

# Validation limits
MAX_REPOSITORY_OWNER_LENGTH = 39  # GitHub username maximum length
MAX_REPOSITORY_NAME_LENGTH = 100  # GitHub repository name maximum length
MAX_REF_NAME_LENGTH = 256  # Maximum length for git reference names

# Security token generation
ARTIFACT_SUFFIX_RANDOM_BYTES = 2  # Number of random bytes (4 hex chars) for artifact naming
GITHUB_OUTPUT_DELIMITER_RANDOM_BYTES = 8  # Number of random bytes for output delimiter
