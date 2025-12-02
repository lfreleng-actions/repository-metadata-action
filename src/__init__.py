# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Repository Metadata Action - Python Implementation

A GitHub Action that extracts comprehensive metadata about the repository,
workflow context, and changes.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("repository-metadata-action")
except PackageNotFoundError:
    # Package not installed, use fallback version
    __version__ = "0.0.0+dev"

__author__ = "The Linux Foundation"
