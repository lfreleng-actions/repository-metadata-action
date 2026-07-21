# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Event metadata extractor.
Detects and categorizes GitHub event types.
"""

from ..models import EventMetadata
from .base import BaseExtractor


class EventExtractor(BaseExtractor):
    """Extracts event type metadata."""

    # Map each simple event name to the boolean flag it sets and a human
    # readable label for debug logging. Push events need extra ref
    # inspection and are handled separately in _classify_push_event.
    _EVENT_FLAGS: dict[str, tuple[str, str]] = {
        "pull_request": ("is_pull_request", "pull request"),
        "pull_request_target": ("is_pull_request", "pull request"),
        "release": ("is_release", "release"),
        "schedule": ("is_schedule", "scheduled"),
        "workflow_dispatch": ("is_workflow_dispatch", "workflow dispatch"),
    }

    def extract(self) -> EventMetadata:
        """
        Extract event type metadata from environment.

        Returns:
            EventMetadata object with event type flags
        """
        self.debug("Extracting event metadata")

        event_name = self.config.GITHUB_EVENT_NAME
        self.info(f"Event name: {event_name}")

        flags: dict[str, bool] = {
            "is_tag_push": False,
            "is_branch_push": False,
            "is_pull_request": False,
            "is_release": False,
            "is_schedule": False,
            "is_workflow_dispatch": False,
            "tag_push_event": False,
        }

        mapped = self._EVENT_FLAGS.get(event_name)
        if mapped:
            flag_name, label = mapped
            flags[flag_name] = True
            self.debug(f"Detected {label} event")
        elif event_name == "push":
            self.debug("Detected push event (determining tag vs branch)")
            self._classify_push_event(flags)

        return EventMetadata(name=event_name, **flags)

    def _classify_push_event(self, flags: dict[str, bool]) -> None:
        """
        Classify a push event as a tag or branch push based on ref type.

        Args:
            flags: Mutable mapping of event flags, updated in place.
        """
        ref_type = self.config.GITHUB_REF_TYPE
        ref_name = self.config.GITHUB_REF_NAME

        if ref_type == "tag":
            flags["is_tag_push"] = True
            self.debug(f"Push event is a tag push: {ref_name}")

            # Check if it's a version tag (v*.*.* semantic versioning)
            if ref_name and self._is_version_tag(ref_name):
                flags["tag_push_event"] = True
                self.info(f"Detected version tag push: {ref_name}")
        elif ref_type == "branch":
            flags["is_branch_push"] = True
            self.debug(f"Push event is a branch push: {ref_name}")

    def _is_version_tag(self, tag_name: str) -> bool:
        """
        Check if tag name matches semantic versioning pattern.

        Pattern: vX.Y or vX.Y.Z with optional pre-release/build metadata
        Examples: v1.0, v1.0.0, v1.2.3-alpha, v2.0.0+build123

        Args:
            tag_name: Tag name to check

        Returns:
            True if tag matches version pattern
        """
        import re

        # Regex for semantic version tags with v prefix
        # Matches: v[major].[minor] or v[major].[minor].[patch]
        # With optional pre-release (-xxx) or build metadata (+xxx)
        pattern = r"^v[0-9]+(\.[0-9]+){1,2}([-\+][A-Za-z0-9\.-]+)?$"
        return bool(re.match(pattern, tag_name))
