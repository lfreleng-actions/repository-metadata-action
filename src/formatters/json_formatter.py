# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
JSON formatter for metadata output.
Provides both compact and pretty-printed JSON formatting.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import CompleteMetadata


class JsonFormatter:
    """Formats metadata as JSON."""

    def format(self, metadata: "CompleteMetadata", pretty: bool = False, include_comment: bool = False) -> str:
        """
        Format metadata as JSON string.

        Args:
            metadata: CompleteMetadata object to format
            pretty: If True, use pretty-printing with indentation
            include_comment: Whether to include Gerrit comment field (default: False for security)

        Returns:
            JSON string representation of metadata
        """
        return metadata.to_json(pretty=pretty, include_comment=include_comment)

    def format_compact(self, metadata: "CompleteMetadata", include_comment: bool = False) -> str:
        """
        Format metadata as compact JSON (single line, no whitespace).

        Args:
            metadata: CompleteMetadata object to format
            include_comment: Whether to include Gerrit comment field (default: False for security)

        Returns:
            Compact JSON string
        """
        return self.format(metadata, pretty=False, include_comment=include_comment)

    def format_pretty(self, metadata: "CompleteMetadata", include_comment: bool = False) -> str:
        """
        Format metadata as pretty-printed JSON (indented, readable).

        Args:
            metadata: CompleteMetadata object to format
            include_comment: Whether to include Gerrit comment field (default: False for security)

        Returns:
            Pretty-printed JSON string
        """
        return self.format(metadata, pretty=True, include_comment=include_comment)
