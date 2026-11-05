# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Tests for WorkflowRunExtractor.
"""

import logging
from unittest.mock import Mock

import pytest

from src.extractors.workflow_run import WorkflowRunExtractor
from src.models import WorkflowRunMetadata


def _extract(config):
    """Run the extractor against a config."""
    return WorkflowRunExtractor(config).extract()


@pytest.fixture
def mock_config():
    """Create a mock config carrying every workflow run variable."""
    config = Mock()
    config.GITHUB_REPOSITORY = "owner/repo"
    config.GITHUB_SERVER_URL = "https://github.com"
    config.GITHUB_RUN_ID = 1234567890
    config.GITHUB_RUN_ATTEMPT = 1
    config.GITHUB_RUN_NUMBER = 42
    config.GITHUB_WORKFLOW = "CI"
    config.GITHUB_WORKFLOW_REF = "owner/repo/.github/workflows/ci.yaml@refs/heads/main"
    config.GITHUB_JOB = "build"
    config.DEBUG_MODE = False
    return config


class TestWorkflowRunExtractor:
    """Test suite for WorkflowRunExtractor."""

    def test_extract_all_fields(self, mock_config):
        """Test extraction with every field populated."""
        result = _extract(mock_config)

        assert isinstance(result, WorkflowRunMetadata)
        assert result.run_id == 1234567890
        assert result.run_attempt == 1
        assert result.run_number == 42
        assert result.workflow == "CI"
        assert result.workflow_ref == "owner/repo/.github/workflows/ci.yaml@refs/heads/main"
        assert result.job == "build"
        assert result.run_url == "https://github.com/owner/repo/actions/runs/1234567890"

    def test_first_attempt_url_has_no_attempt_suffix(self, mock_config):
        """Test the first attempt links to the run itself."""
        result = _extract(mock_config)

        assert "/attempts/" not in result.run_url

    def test_retried_attempt_url_names_the_attempt(self, mock_config):
        """Test a re-run links to its own attempt."""
        mock_config.GITHUB_RUN_ATTEMPT = "2"

        result = _extract(mock_config)

        assert result.run_attempt == 2
        assert result.run_url == (
            "https://github.com/owner/repo/actions/runs/1234567890/attempts/2"
        )

    def test_string_integers_are_parsed(self, mock_config):
        """Test raw string values are parsed into integers."""
        mock_config.GITHUB_RUN_ID = "555"
        mock_config.GITHUB_RUN_NUMBER = "7"

        result = _extract(mock_config)

        assert result.run_id == 555
        assert result.run_number == 7

    def test_non_numeric_run_id_warns(self, mock_config, caplog):
        """Test a non-numeric run ID becomes None with a warning."""
        mock_config.GITHUB_RUN_ID = "not-a-number"

        with caplog.at_level(logging.WARNING):
            result = _extract(mock_config)

        assert result.run_id is None
        assert result.run_url == ""
        assert "not-a-number" in caplog.text

    def test_non_numeric_attempt_and_number_warn(self, mock_config, caplog):
        """Test non-numeric attempt and number become None with warnings."""
        mock_config.GITHUB_RUN_ATTEMPT = "x"
        mock_config.GITHUB_RUN_NUMBER = "y"

        with caplog.at_level(logging.WARNING):
            result = _extract(mock_config)

        assert result.run_attempt is None
        assert result.run_number is None
        assert result.run_url == "https://github.com/owner/repo/actions/runs/1234567890"
        assert caplog.text.count("Failed to parse") == 2

    def test_unset_variables(self, mock_config):
        """Test unset variables give None integers and empty strings."""
        mock_config.GITHUB_RUN_ID = None
        mock_config.GITHUB_RUN_ATTEMPT = None
        mock_config.GITHUB_RUN_NUMBER = None
        mock_config.GITHUB_WORKFLOW = None
        mock_config.GITHUB_WORKFLOW_REF = None
        mock_config.GITHUB_JOB = None

        result = _extract(mock_config)

        assert result.run_id is None
        assert result.run_attempt is None
        assert result.run_number is None
        assert result.workflow == ""
        assert result.workflow_ref == ""
        assert result.job == ""
        assert result.run_url == ""

    def test_server_url_trailing_slash(self, mock_config):
        """Test a trailing slash on the server URL is not doubled."""
        mock_config.GITHUB_SERVER_URL = "https://ghe.example.com/"

        result = _extract(mock_config)

        assert result.run_url == "https://ghe.example.com/owner/repo/actions/runs/1234567890"

    def test_missing_server_url_defaults_to_github(self, mock_config):
        """Test an unset server URL falls back to github.com."""
        mock_config.GITHUB_SERVER_URL = None

        result = _extract(mock_config)

        assert result.run_url == "https://github.com/owner/repo/actions/runs/1234567890"
