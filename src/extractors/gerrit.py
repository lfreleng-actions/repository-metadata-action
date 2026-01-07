# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Gerrit metadata extraction from multiple sources.
Supports workflow_dispatch inputs, environment variables, and commit messages.
"""

import json
import re
from typing import TYPE_CHECKING, Any

from ..models import GerritMetadata
from .base import BaseExtractor

import ijson

if TYPE_CHECKING:
    from ..config import Config
    from ..git_operations import GitOperations


class GerritExtractor(BaseExtractor):
    """Extracts Gerrit-related metadata from various sources."""

    def __init__(
        self,
        config: "Config",
        git_ops: "GitOperations | None" = None,
        **kwargs
    ):
        """
        Initialize Gerrit extractor.

        Args:
            config: Configuration object
            git_ops: Optional git operations handler
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(config, **kwargs)
        self.git_ops = git_ops

    def extract(self) -> GerritMetadata | None:
        """
        Extract Gerrit metadata from available sources.

        Tries sources in order of preference:
        1. workflow_dispatch event inputs (gerrit_json or gerrit_to_platform inputs)
        2. Environment variables (gerrit_to_platform environment variables)
        3. Commit message (Change-Id trailer)

        Returns:
            GerritMetadata object if Gerrit data found, None otherwise
        """
        self.debug("Checking for Gerrit metadata")

        # Try sources in order of preference
        gerrit_data = None
        source = None

        if self.config.GITHUB_EVENT_NAME == "workflow_dispatch":
            gerrit_data, source = self._extract_from_workflow_dispatch()

        if not gerrit_data:
            gerrit_data, source = self._extract_from_environment()

        if not gerrit_data:
            gerrit_data, source = self._extract_from_commit_message()

        if gerrit_data:
            self.info(f"Gerrit metadata found from: {source}")
            # Ensure source is included in the data
            gerrit_data["source"] = source or ""
            return GerritMetadata(**gerrit_data)

        self.debug("No Gerrit metadata found - returning empty GerritMetadata")
        # Always return GerritMetadata object (with empty fields) instead of None
        # This ensures Gerrit fields are always present in JSON output
        return GerritMetadata(
            branch="",
            change_id="",
            change_number="",
            change_url="",
            event_type="",
            patchset_number="",
            patchset_revision="",
            project="",
            refspec="",
            comment="",
            source="none"
        )

    def _extract_from_workflow_dispatch(self) -> tuple[dict[str, Any] | None, str | None]:
        """
        Extract from workflow_dispatch event inputs.

        Checks for:
        1. Consolidated gerrit_json input (preferred)
        2. Individual gerrit_to_platform inputs

        Returns:
            Tuple of (gerrit_data dict, source description) or (None, None)
        """
        if not self.config.GITHUB_EVENT_PATH or not self.config.GITHUB_EVENT_PATH.exists():
            self.debug("No event payload available")
            return None, None

        try:
            with open(self.config.GITHUB_EVENT_PATH, "rb") as f:
                parser = ijson.items(f, "inputs")
                inputs: dict[str, Any] = next(parser, {})

            # Check for consolidated gerrit_json input first
            gerrit_json = inputs.get("gerrit_json")
            if gerrit_json:
                try:
                    # Parse JSON if it's a string
                    if isinstance(gerrit_json, str):
                        data = json.loads(gerrit_json)
                    else:
                        data = gerrit_json

                    # Filter out comment unless explicitly enabled
                    if not self.config.GERRIT_INCLUDE_COMMENT and "comment" in data:
                        data.pop("comment")

                    self.debug("Found gerrit_json input")
                    return data, "workflow_dispatch (gerrit_json)"

                except json.JSONDecodeError as e:
                    self.warning(f"Invalid JSON in gerrit_json input: {e}")

            # Fallback to individual GERRIT_* inputs
            gerrit_data = self._extract_gerrit_fields(inputs)
            if self._has_any_gerrit_data(gerrit_data):
                self.debug("Found gerrit_to_platform inputs")
                return gerrit_data, "workflow_dispatch (gerrit_to_platform inputs)"

        except Exception as e:
            self.error("Failed to extract Gerrit data from workflow_dispatch", e)

        return None, None

    def _extract_from_environment(self) -> tuple[dict[str, Any] | None, str | None]:
        """
        Extract from environment variables.

        Checks for gerrit_to_platform environment variables set externally.

        Returns:
            Tuple of (gerrit_data dict, source description) or (None, None)
        """
        # Check if any environment variables were set via config
        # Convert to strings, empty string if None
        env_data = {
            "branch": self.config.GERRIT_BRANCH or "",
            "change_id": self.config.GERRIT_CHANGE_ID or "",
            "change_number": self.config.GERRIT_CHANGE_NUMBER or "",
            "change_url": self.config.GERRIT_CHANGE_URL or "",
            "event_type": self.config.GERRIT_EVENT_TYPE or "",
            "patchset_number": self.config.GERRIT_PATCHSET_NUMBER or "",
            "patchset_revision": self.config.GERRIT_PATCHSET_REVISION or "",
            "project": self.config.GERRIT_PROJECT or "",
            "refspec": self.config.GERRIT_REFSPEC or "",
        }

        if self.config.GERRIT_INCLUDE_COMMENT:
            env_data["comment"] = self.config.GERRIT_COMMENT or ""

        if self._has_any_gerrit_data(env_data):
            self.debug("Found gerrit_to_platform environment variables")
            return env_data, "environment variables"

        return None, None

    def _extract_from_commit_message(self) -> tuple[dict[str, Any] | None, str | None]:
        """
        Extract Change-Id from commit message.

        Looks for Gerrit Change-Id trailer in the commit message.
        Format: Change-Id: I<40-hex-digits>

        Returns:
            Tuple of (gerrit_data dict, source description) or (None, None)
        """
        if not self.git_ops or not self.git_ops.has_git_repo():
            self.debug("Git repository not available for commit message check")
            return None, None

        try:
            # Get full commit message (including body/trailers)
            commit_message = self.git_ops.get_commit_message_full(self.config.GITHUB_SHA)
            if not commit_message:
                self.debug("No commit message available")
                return None, None

            # Look for Change-Id trailer
            # Pattern: Change-Id: I<40-hex-chars> at start of line
            match = re.search(
                r"^Change-Id:\s+(I[0-9a-fA-F]{40})$",
                commit_message,
                re.MULTILINE
            )

            if match:
                change_id = match.group(1)
                self.debug(f"Found Change-Id in commit message: {change_id}")

                # Build minimal Gerrit data from commit
                gerrit_data = {
                    "change_id": change_id,
                    "branch": self.config.GITHUB_REF_NAME or "",
                    "patchset_revision": self.config.GITHUB_SHA or "",
                    "event_type": "ref-updated",
                    "change_number": "",
                    "change_url": "",
                    "patchset_number": "",
                    "project": "",
                    "refspec": "",
                    "comment": "",
                }

                return gerrit_data, "commit message (Change-Id trailer)"
            self.debug("No Change-Id found in commit message")

        except Exception as e:
            self.debug(f"Failed to extract Change-Id from commit: {e}")

        return None, None

    def _extract_gerrit_fields(self, source: dict[str, Any]) -> dict[str, str]:
        """
        Extract Gerrit fields from a dictionary source.

        Tries multiple name variations for each field:
        - lowercase (e.g., 'branch')
        - GERRIT_ prefix uppercase (e.g., 'GERRIT_BRANCH')
        - gerrit_ prefix lowercase (e.g., 'gerrit_branch')

        Args:
            source: Dictionary to extract fields from

        Returns:
            Dictionary with standardized field names
        """
        fields = [
            "branch",
            "change_id",
            "change_number",
            "change_url",
            "event_type",
            "patchset_number",
            "patchset_revision",
            "project",
            "refspec",
        ]

        if self.config.GERRIT_INCLUDE_COMMENT:
            fields.append("comment")

        result = {}
        for field in fields:
            # Try different name variations
            value = (
                source.get(field) or
                source.get(f"GERRIT_{field.upper()}") or
                source.get(f"gerrit_{field}")
            )

            # Convert to string, empty string if None or "null"
            result[field] = str(value) if value and value != "null" else ""

        return result

    def _has_any_gerrit_data(self, data: dict[str, str]) -> bool:
        """
        Check if dictionary contains any non-None Gerrit data.

        Args:
            data: Dictionary to check

        Returns:
            True if any value is not empty
        """
        return any(value for value in data.values())
