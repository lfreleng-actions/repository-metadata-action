# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for PullRequestExtractor.
"""

import json
from typing import Any
from unittest.mock import Mock

import pytest

from src.extractors.pull_request import PullRequestExtractor
from src.models import PullRequestMetadata


@pytest.fixture
def mock_config():
    """Create a mock config object."""
    config = Mock()
    config.GITHUB_EVENT_NAME = "pull_request"
    config.GITHUB_REF = "refs/pull/123/merge"
    config.GITHUB_HEAD_REF = "feature/new-feature"
    config.GITHUB_BASE_REF = "main"
    config.PR_HEAD_REPO_FORK = False
    config.GITHUB_TOKEN = None
    config.GITHUB_EVENT_PATH = None
    config.GITHUB_REPOSITORY = "owner/repo"
    config.GITHUB_RUN_ID = "12345"
    config.GITHUB_WORKFLOW = "CI"
    config.DEBUG_MODE = False
    return config


@pytest.fixture
def mock_github_api():
    """Create a mock GitHub API client."""
    api = Mock()
    api.get_pr_metadata = Mock(return_value={"commits_count": 5})
    return api


class TestPullRequestExtractor:
    """Test suite for PullRequestExtractor."""

    def test_extract_basic_pr_info(self, mock_config):
        """Test extraction of basic PR information."""
        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert isinstance(result, PullRequestMetadata)
        assert result.number == 123
        assert result.source_branch == "feature/new-feature"
        assert result.target_branch == "main"
        assert result.is_fork is False
        assert result.commits_count is None

    def test_extract_not_pull_request_event(self, mock_config):
        """Test extraction when not a pull request event."""
        mock_config.GITHUB_EVENT_NAME = "push"

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        # Should return empty metadata
        assert result.number is None
        assert result.source_branch is None
        assert result.target_branch is None
        assert result.commits_count is None
        assert result.is_fork is False

    def test_extract_pull_request_target_event(self, mock_config):
        """Test extraction for pull_request_target event."""
        mock_config.GITHUB_EVENT_NAME = "pull_request_target"

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.number == 123
        assert result.source_branch == "feature/new-feature"
        assert result.target_branch == "main"

    def test_extract_pr_number_from_merge_ref(self, mock_config):
        """Test PR number extraction from merge ref."""
        mock_config.GITHUB_REF = "refs/pull/456/merge"

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.number == 456

    def test_extract_pr_number_from_head_ref(self, mock_config):
        """Test PR number extraction from head ref."""
        mock_config.GITHUB_REF = "refs/pull/789/head"

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.number == 789

    def test_extract_pr_number_large(self, mock_config):
        """Test extraction with large PR number."""
        mock_config.GITHUB_REF = "refs/pull/99999/merge"

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.number == 99999

    def test_extract_pr_number_invalid_format(self, mock_config):
        """Test extraction with invalid GITHUB_REF format."""
        mock_config.GITHUB_REF = "refs/heads/main"

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        # Should return empty metadata when PR number can't be extracted
        assert result.number is None

    def test_extract_pr_number_missing_ref(self, mock_config):
        """Test extraction when GITHUB_REF is missing."""
        mock_config.GITHUB_REF = None

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.number is None

    def test_extract_pr_number_empty_ref(self, mock_config):
        """Test extraction when GITHUB_REF is empty."""
        mock_config.GITHUB_REF = ""

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.number is None

    def test_extract_pr_number_malformed(self, mock_config):
        """Test extraction with malformed PR ref."""
        test_cases = [
            "refs/pull/abc/merge",  # Non-numeric
            "refs/pull//merge",  # Empty number
            "pull/123/merge",  # Missing refs/
            "refs/pull/123",  # Missing /merge or /head
        ]

        for ref in test_cases:
            mock_config.GITHUB_REF = ref
            extractor = PullRequestExtractor(mock_config)
            result = extractor.extract()
            assert result.number is None

    def test_extract_with_fork(self, mock_config):
        """Test extraction when PR is from a fork."""
        mock_config.PR_HEAD_REPO_FORK = True

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.is_fork is True
        assert result.number == 123

    def test_extract_source_branch_variations(self, mock_config):
        """Test various source branch formats."""
        test_branches = [
            "feature/new-feature",
            "bugfix/fix-123",
            "hotfix/critical",
            "release/v1.0.0",
            "user/feature",
        ]

        for branch in test_branches:
            mock_config.GITHUB_HEAD_REF = branch
            extractor = PullRequestExtractor(mock_config)
            result = extractor.extract()
            assert result.source_branch == branch

    def test_extract_target_branch_variations(self, mock_config):
        """Test various target branch formats."""
        test_branches = [
            "main",
            "master",
            "develop",
            "release/v2.0",
        ]

        for branch in test_branches:
            mock_config.GITHUB_BASE_REF = branch
            extractor = PullRequestExtractor(mock_config)
            result = extractor.extract()
            assert result.target_branch == branch

    def test_extract_no_source_branch(self, mock_config):
        """Test extraction when source branch is not available."""
        mock_config.GITHUB_HEAD_REF = None

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.source_branch is None
        assert result.number == 123  # Other fields still work

    def test_extract_no_target_branch(self, mock_config):
        """Test extraction when target branch is not available."""
        mock_config.GITHUB_BASE_REF = None

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.target_branch is None
        assert result.number == 123

    def test_extract_with_api_commits_count(self, mock_config, mock_github_api):
        """Test extraction with commits count from API."""
        mock_config.GITHUB_TOKEN = "test-token"

        extractor = PullRequestExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.commits_count == 5
        mock_github_api.get_pr_metadata.assert_called_once_with("owner/repo", 123)

    def test_extract_api_no_token(self, mock_config, mock_github_api):
        """Test that API is not called without token."""
        mock_config.GITHUB_TOKEN = None

        extractor = PullRequestExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.commits_count is None
        mock_github_api.get_pr_metadata.assert_not_called()

    def test_extract_api_failure(self, mock_config, mock_github_api):
        """Test extraction when API call fails."""
        mock_config.GITHUB_TOKEN = "test-token"
        mock_github_api.get_pr_metadata.side_effect = Exception("API error")

        extractor = PullRequestExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        # Should not crash, falls back to None
        assert result.number == 123
        assert result.commits_count is None

    def test_extract_api_no_commits_count(self, mock_config, mock_github_api):
        """Test extraction when API returns no commits count."""
        mock_config.GITHUB_TOKEN = "test-token"
        mock_github_api.get_pr_metadata.return_value = {}

        extractor = PullRequestExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.commits_count is None

    def test_extract_api_zero_commits(self, mock_config, mock_github_api):
        """Test extraction when API returns zero commits."""
        mock_config.GITHUB_TOKEN = "test-token"
        mock_github_api.get_pr_metadata.return_value = {"commits_count": 0}

        extractor = PullRequestExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.commits_count == 0

    def test_extract_from_event_payload(self, mock_config, tmp_path):
        """Test extraction of commits count from event payload."""
        # Create event payload file
        event_path = tmp_path / "event.json"
        event_data = {"pull_request": {"number": 123, "commits": 7}}
        event_path.write_text(json.dumps(event_data))
        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.commits_count == 7

    def test_extract_from_event_payload_no_commits(self, mock_config, tmp_path):
        """Test extraction when event payload has no commits field."""
        event_path = tmp_path / "event.json"
        event_data = {"pull_request": {"number": 123}}
        event_path.write_text(json.dumps(event_data))
        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.commits_count is None

    def test_extract_from_event_payload_no_pr_object(self, mock_config, tmp_path):
        """Test extraction when event payload has no pull_request object."""
        event_path = tmp_path / "event.json"
        event_data = {"action": "opened"}
        event_path.write_text(json.dumps(event_data))
        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.commits_count is None

    def test_extract_event_payload_file_not_found(self, mock_config, tmp_path):
        """Test extraction when event payload file doesn't exist."""
        event_path = tmp_path / "nonexistent.json"
        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        # Should not crash
        assert result.commits_count is None

    def test_extract_event_payload_invalid_json(self, mock_config, tmp_path):
        """Test extraction when event payload is invalid JSON."""
        event_path = tmp_path / "event.json"
        event_path.write_text("not valid json {")
        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        # Should handle exception gracefully
        assert result.commits_count is None

    def test_extract_api_takes_precedence_over_event(self, mock_config, mock_github_api, tmp_path):
        """Test that API data takes precedence over event payload."""
        mock_config.GITHUB_TOKEN = "test-token"

        # Set up event payload with different commits count
        event_path = tmp_path / "event.json"
        event_data = {"pull_request": {"commits": 10}}
        event_path.write_text(json.dumps(event_data))
        mock_config.GITHUB_EVENT_PATH = event_path

        # API returns 5 commits
        mock_github_api.get_pr_metadata.return_value = {"commits_count": 5}

        extractor = PullRequestExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        # Should use API value
        assert result.commits_count == 5

    def test_extract_event_payload_fallback_on_api_failure(
        self, mock_config, mock_github_api, tmp_path
    ):
        """Test fallback to event payload when API fails."""
        mock_config.GITHUB_TOKEN = "test-token"
        mock_github_api.get_pr_metadata.side_effect = Exception("API error")

        # Set up event payload
        event_path = tmp_path / "event.json"
        event_data = {"pull_request": {"commits": 8}}
        event_path.write_text(json.dumps(event_data))
        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = PullRequestExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        # Should use event payload as fallback
        assert result.commits_count == 8

    def test_extract_pr_number_method(self, mock_config):
        """Test _extract_pr_number method directly."""
        extractor = PullRequestExtractor(mock_config)

        # Valid formats
        mock_config.GITHUB_REF = "refs/pull/123/merge"
        assert extractor._extract_pr_number() == 123

        mock_config.GITHUB_REF = "refs/pull/456/head"
        assert extractor._extract_pr_number() == 456

        mock_config.GITHUB_REF = "refs/pull/1/merge"
        assert extractor._extract_pr_number() == 1

        # Invalid formats
        mock_config.GITHUB_REF = "refs/heads/main"
        assert extractor._extract_pr_number() is None

        mock_config.GITHUB_REF = None
        assert extractor._extract_pr_number() is None

        mock_config.GITHUB_REF = ""
        assert extractor._extract_pr_number() is None

    def test_extract_commits_from_event_method(self, mock_config, tmp_path):
        """Test _extract_commits_from_event method directly."""
        extractor = PullRequestExtractor(mock_config)

        # Valid event with commits
        event_path = tmp_path / "event1.json"
        event_data = {"pull_request": {"commits": 3}}
        event_path.write_text(json.dumps(event_data))
        mock_config.GITHUB_EVENT_PATH = event_path
        assert extractor._extract_commits_from_event() == 3

        # Event with zero commits
        event_path2 = tmp_path / "event2.json"
        event_data2 = {"pull_request": {"commits": 0}}
        event_path2.write_text(json.dumps(event_data2))
        mock_config.GITHUB_EVENT_PATH = event_path2
        assert extractor._extract_commits_from_event() == 0

        # Event without commits field
        event_path3 = tmp_path / "event3.json"
        event_data3: dict[str, Any] = {"pull_request": {}}
        event_path3.write_text(json.dumps(event_data3))
        mock_config.GITHUB_EVENT_PATH = event_path3
        assert extractor._extract_commits_from_event() is None

        # No event path
        mock_config.GITHUB_EVENT_PATH = None
        assert extractor._extract_commits_from_event() is None

    def test_logging_output(self, mock_config, caplog):
        """Test that appropriate logging messages are generated."""
        import logging

        caplog.set_level(logging.INFO)

        mock_config.DEBUG_MODE = True

        extractor = PullRequestExtractor(mock_config)
        _ = extractor.extract()

        assert "Pull request: #123" in caplog.text

    def test_logging_not_pr_event(self, mock_config, caplog):
        """Test logging when not a PR event."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.DEBUG_MODE = True

        extractor = PullRequestExtractor(mock_config)
        _ = extractor.extract()

        assert "Not a pull request event" in caplog.text

    def test_logging_api_fetch(self, mock_config, mock_github_api, caplog):
        """Test logging when fetching from API."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.DEBUG_MODE = True

        extractor = PullRequestExtractor(mock_config, github_api=mock_github_api)
        _ = extractor.extract()

        assert "Fetching PR metadata from GitHub API" in caplog.text
        assert "PR has 5 commits" in caplog.text

    def test_logging_api_failure(self, mock_config, mock_github_api, caplog):
        """Test logging when API fails."""
        import logging

        caplog.set_level(logging.WARNING)

        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.DEBUG_MODE = True
        mock_github_api.get_pr_metadata.side_effect = Exception("Network error")

        extractor = PullRequestExtractor(mock_config, github_api=mock_github_api)
        _ = extractor.extract()

        assert "Failed to fetch PR metadata from API" in caplog.text

    def test_logging_fork_detection(self, mock_config, caplog):
        """Test logging when PR is from fork."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.PR_HEAD_REPO_FORK = True
        mock_config.DEBUG_MODE = True

        extractor = PullRequestExtractor(mock_config)
        _ = extractor.extract()

        assert "PR is from a fork" in caplog.text

    def test_logging_branches(self, mock_config, caplog):
        """Test logging of source and target branches."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.DEBUG_MODE = True

        extractor = PullRequestExtractor(mock_config)
        _ = extractor.extract()

        assert "PR source branch: feature/new-feature" in caplog.text
        assert "PR target branch: main" in caplog.text

    def test_pr_metadata_model_compliance(self, mock_config):
        """Test that extracted data complies with PullRequestMetadata model."""
        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        # Verify model fields exist
        assert hasattr(result, "number")
        assert hasattr(result, "source_branch")
        assert hasattr(result, "target_branch")
        assert hasattr(result, "commits_count")
        assert hasattr(result, "is_fork")

        # Verify types
        assert isinstance(result.number, int) or result.number is None
        assert isinstance(result.source_branch, str) or result.source_branch is None
        assert isinstance(result.target_branch, str) or result.target_branch is None
        assert isinstance(result.commits_count, int) or result.commits_count is None
        assert isinstance(result.is_fork, bool)

    def test_extract_no_api_provided(self, mock_config):
        """Test extraction when no API client is provided."""
        extractor = PullRequestExtractor(mock_config, github_api=None)
        result = extractor.extract()

        assert result.number == 123
        assert result.commits_count is None

    def test_extract_with_unicode_branches(self, mock_config):
        """Test extraction with unicode characters in branch names."""
        mock_config.GITHUB_HEAD_REF = "feature/新功能"
        mock_config.GITHUB_BASE_REF = "メイン"

        extractor = PullRequestExtractor(mock_config)
        result = extractor.extract()

        assert result.source_branch == "feature/新功能"
        assert result.target_branch == "メイン"

    def test_extract_with_special_chars_in_branches(self, mock_config):
        """Test extraction with special characters in branch names."""
        test_cases = [
            ("feature/fix-bug-#123", "main"),
            ("user/branch_name", "develop"),
            ("hotfix/v1.0.0-patch", "release/v1.0"),
        ]

        for source, target in test_cases:
            mock_config.GITHUB_HEAD_REF = source
            mock_config.GITHUB_BASE_REF = target
            extractor = PullRequestExtractor(mock_config)
            result = extractor.extract()
            assert result.source_branch == source
            assert result.target_branch == target
