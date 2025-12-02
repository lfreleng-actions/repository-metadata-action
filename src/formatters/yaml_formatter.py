# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
YAML formatter for metadata output.
Provides YAML formatting with fallback to Python's yaml module.
"""

from typing import TYPE_CHECKING

import yaml  # type: ignore[import-untyped]  # PyYAML doesn't have complete type stubs

if TYPE_CHECKING:
    from ..models import CompleteMetadata


class YamlFormatter:
    """Formats metadata as YAML."""

    def format(self, metadata: "CompleteMetadata", include_comment: bool = False) -> str:
        """
        Format metadata as YAML string.

        Args:
            metadata: CompleteMetadata object to format
            include_comment: Whether to include Gerrit comment field (default: False for security)

        Returns:
            YAML string representation of metadata
        """
        # Convert to dictionary first
        data = metadata.to_dict(include_comment=include_comment)

        # Format as YAML
        yaml_str = yaml.safe_dump(
            data,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True
        )

        return str(yaml_str)
