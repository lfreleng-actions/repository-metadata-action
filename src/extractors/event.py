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

    def extract(self) -> EventMetadata:
        """
        Extract event type metadata from environment.

        Returns:
            EventMetadata object with event type flags
        """
        self.debug("Extracting event metadata")

        event_name = self.config.GITHUB_EVENT_NAME
        self.info(f"Event name: {event_name}")

        # Initialize all flags to False
        is_tag_push = False
        is_branch_push = False
        is_pull_request = False
        is_release = False
        is_schedule = False
        is_workflow_dispatch = False
        tag_push_event = False

        # Detect event type
        if event_name in ["pull_request", "pull_request_target"]:
            is_pull_request = True
            self.debug("Detected pull request event")
        elif event_name == "release":
            is_release = True
            self.debug("Detected release event")
        elif event_name == "schedule":
            is_schedule = True
            self.debug("Detected scheduled event")
        elif event_name == "workflow_dispatch":
            is_workflow_dispatch = True
            self.debug("Detected workflow dispatch event")
        elif event_name == "push":
            # For push events, need to determine if it's tag or branch
            self.debug("Detected push event (determining tag vs branch)")

        # Determine if push is tag or branch based on ref type
        if event_name == "push":
            ref_type = self.config.GITHUB_REF_TYPE
            ref_name = self.config.GITHUB_REF_NAME

            if ref_type == "tag":
                is_tag_push = True
                self.debug(f"Push event is a tag push: {ref_name}")

                # Check if it's a version tag (v*.*.* semantic versioning)
                if ref_name and self._is_version_tag(ref_name):
                    tag_push_event = True
                    self.info(f"Detected version tag push: {ref_name}")
            elif ref_type == "branch":
                is_branch_push = True
                self.debug(f"Push event is a branch push: {ref_name}")

        return EventMetadata(
            name=event_name,
            is_tag_push=is_tag_push,
            is_branch_push=is_branch_push,
            is_pull_request=is_pull_request,
            is_release=is_release,
            is_schedule=is_schedule,
            is_workflow_dispatch=is_workflow_dispatch,
            tag_push_event=tag_push_event
        )

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
