# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for EventExtractor.
"""

from unittest.mock import Mock

import pytest

from src.extractors.event import EventExtractor
from src.models import EventMetadata


@pytest.fixture
def mock_config():
    """Create a mock config object."""
    config = Mock()
    config.GITHUB_EVENT_NAME = "push"
    config.GITHUB_REF_TYPE = "branch"
    config.GITHUB_REF_NAME = "main"
    config.GITHUB_RUN_ID = "12345"
    config.GITHUB_WORKFLOW = "CI"
    config.DEBUG_MODE = False
    return config


class TestEventExtractor:
    """Test suite for EventExtractor."""

    def test_pull_request_event(self, mock_config):
        """Test extraction for pull_request event."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert isinstance(result, EventMetadata)
        assert result.name == "pull_request"
        assert result.is_pull_request is True
        assert result.is_branch_push is False
        assert result.is_tag_push is False
        assert result.is_release is False
        assert result.is_schedule is False
        assert result.is_workflow_dispatch is False
        assert result.tag_push_event is False

    def test_pull_request_target_event(self, mock_config):
        """Test extraction for pull_request_target event."""
        mock_config.GITHUB_EVENT_NAME = "pull_request_target"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "pull_request_target"
        assert result.is_pull_request is True
        assert result.is_branch_push is False
        assert result.is_tag_push is False

    def test_release_event(self, mock_config):
        """Test extraction for release event."""
        mock_config.GITHUB_EVENT_NAME = "release"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "release"
        assert result.is_release is True
        assert result.is_pull_request is False
        assert result.is_branch_push is False
        assert result.is_tag_push is False

    def test_schedule_event(self, mock_config):
        """Test extraction for schedule event."""
        mock_config.GITHUB_EVENT_NAME = "schedule"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "schedule"
        assert result.is_schedule is True
        assert result.is_pull_request is False
        assert result.is_branch_push is False

    def test_workflow_dispatch_event(self, mock_config):
        """Test extraction for workflow_dispatch event."""
        mock_config.GITHUB_EVENT_NAME = "workflow_dispatch"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "workflow_dispatch"
        assert result.is_workflow_dispatch is True
        assert result.is_pull_request is False

    def test_branch_push_event(self, mock_config):
        """Test extraction for branch push event."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "feature/new-feature"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "push"
        assert result.is_branch_push is True
        assert result.is_tag_push is False
        assert result.tag_push_event is False
        assert result.is_pull_request is False

    def test_tag_push_event_non_version(self, mock_config):
        """Test extraction for non-version tag push event."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "my-tag"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "push"
        assert result.is_tag_push is True
        assert result.is_branch_push is False
        assert result.tag_push_event is False  # Not a version tag

    def test_tag_push_event_version_v1_0(self, mock_config):
        """Test extraction for version tag push (v1.0)."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "v1.0"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.is_tag_push is True
        assert result.tag_push_event is True

    def test_tag_push_event_version_v1_0_0(self, mock_config):
        """Test extraction for version tag push (v1.0.0)."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "v1.0.0"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.is_tag_push is True
        assert result.tag_push_event is True

    def test_tag_push_event_version_v2_3_4(self, mock_config):
        """Test extraction for version tag push (v2.3.4)."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "v2.3.4"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.is_tag_push is True
        assert result.tag_push_event is True

    def test_tag_push_event_version_with_prerelease(self, mock_config):
        """Test extraction for version tag with pre-release."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "v1.0.0-alpha"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.is_tag_push is True
        assert result.tag_push_event is True

    def test_tag_push_event_version_with_build_metadata(self, mock_config):
        """Test extraction for version tag with build metadata."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "v2.0.0+build123"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.is_tag_push is True
        assert result.tag_push_event is True

    def test_tag_push_event_version_complex(self, mock_config):
        """Test extraction for complex version tag."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "v1.2.3-beta.1"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.is_tag_push is True
        assert result.tag_push_event is True

    def test_tag_push_event_not_version_no_v_prefix(self, mock_config):
        """Test that tags without 'v' prefix are not version tags."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "1.0.0"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.is_tag_push is True
        assert result.tag_push_event is False

    def test_tag_push_event_not_version_invalid_format(self, mock_config):
        """Test that invalid version formats are not version tags."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "vX.Y.Z"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.is_tag_push is True
        assert result.tag_push_event is False

    def test_tag_push_event_not_version_only_major(self, mock_config):
        """Test that single version number is not a version tag."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "v1"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.is_tag_push is True
        assert result.tag_push_event is False

    def test_is_version_tag_method(self, mock_config):
        """Test the _is_version_tag method directly."""
        extractor = EventExtractor(mock_config)

        # Valid version tags
        assert extractor._is_version_tag("v1.0") is True
        assert extractor._is_version_tag("v1.0.0") is True
        assert extractor._is_version_tag("v10.20.30") is True
        assert extractor._is_version_tag("v1.2.3-alpha") is True
        assert extractor._is_version_tag("v1.2.3+build") is True
        assert extractor._is_version_tag("v1.2.3-rc.1") is True

        # Invalid version tags
        assert extractor._is_version_tag("1.0.0") is False  # No v prefix
        assert extractor._is_version_tag("v1") is False  # Only major
        assert extractor._is_version_tag("vA.B.C") is False  # Not numbers
        assert extractor._is_version_tag("v1.0.0.0") is False  # Too many parts
        assert extractor._is_version_tag("tag-name") is False
        assert extractor._is_version_tag("release") is False
        assert extractor._is_version_tag("") is False

    def test_unknown_event_type(self, mock_config):
        """Test handling of unknown event type."""
        mock_config.GITHUB_EVENT_NAME = "unknown_event"

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "unknown_event"
        assert result.is_pull_request is False
        assert result.is_branch_push is False
        assert result.is_tag_push is False
        assert result.is_release is False
        assert result.is_schedule is False
        assert result.is_workflow_dispatch is False
        assert result.tag_push_event is False

    def test_push_event_no_ref_name(self, mock_config):
        """Test push event with missing ref name."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = None

        extractor = EventExtractor(mock_config)
        result = extractor.extract()

        assert result.is_tag_push is True
        assert result.tag_push_event is False  # Can't determine without ref name

    def test_logging_output(self, mock_config, caplog):
        """Test that appropriate logging messages are generated."""
        import logging

        caplog.set_level(logging.INFO)

        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.DEBUG_MODE = True

        extractor = EventExtractor(mock_config)
        _ = extractor.extract()

        assert "Event name: pull_request" in caplog.text

    def test_logging_tag_push(self, mock_config, caplog):
        """Test logging for tag push event."""
        import logging

        caplog.set_level(logging.INFO)

        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "v1.0.0"
        mock_config.DEBUG_MODE = True

        extractor = EventExtractor(mock_config)
        _ = extractor.extract()

        assert "Detected version tag push: v1.0.0" in caplog.text
