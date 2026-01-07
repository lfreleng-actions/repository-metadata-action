# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for RefExtractor.
"""

from unittest.mock import Mock

import pytest

from src.extractors.ref import RefExtractor
from src.models import RefMetadata


@pytest.fixture
def mock_config():
    """Create a mock config object."""
    config = Mock()
    config.GITHUB_REF_TYPE = "branch"
    config.GITHUB_REF_NAME = "main"
    config.GITHUB_HEAD_REF = None
    config.DEFAULT_BRANCH = None
    config.GITHUB_TOKEN = None
    config.GITHUB_REPOSITORY = "owner/repo"
    config.GITHUB_RUN_ID = "12345"
    config.GITHUB_WORKFLOW = "CI"
    config.DEBUG_MODE = False
    return config


@pytest.fixture
def mock_github_api():
    """Create a mock GitHub API client."""
    api = Mock()
    api.get_default_branch = Mock(return_value="main")
    return api


class TestRefExtractor:
    """Test suite for RefExtractor."""

    def test_extract_branch_main(self, mock_config):
        """Test extraction for main branch."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "main"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert isinstance(result, RefMetadata)
        assert result.branch_name == "main"
        assert result.tag_name is None
        assert result.is_main_branch is True
        assert result.is_default_branch is False  # No DEFAULT_BRANCH set

    def test_extract_branch_master(self, mock_config):
        """Test extraction for master branch."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "master"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name == "master"
        assert result.tag_name is None
        assert result.is_main_branch is True
        assert result.is_default_branch is False

    def test_extract_branch_feature(self, mock_config):
        """Test extraction for feature branch."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "feature/new-feature"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name == "feature/new-feature"
        assert result.tag_name is None
        assert result.is_main_branch is False
        assert result.is_default_branch is False

    def test_extract_branch_with_default_branch_config(self, mock_config):
        """Test extraction with DEFAULT_BRANCH configured."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "main"
        mock_config.DEFAULT_BRANCH = "main"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name == "main"
        assert result.is_main_branch is True
        assert result.is_default_branch is True

    def test_extract_branch_not_default(self, mock_config):
        """Test extraction when branch is not default."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "develop"
        mock_config.DEFAULT_BRANCH = "main"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name == "develop"
        assert result.is_main_branch is False
        assert result.is_default_branch is False

    def test_extract_branch_with_api_default_detection(self, mock_config, mock_github_api):
        """Test extraction with API-based default branch detection."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "main"
        mock_config.GITHUB_TOKEN = "test-token"
        mock_github_api.get_default_branch.return_value = "main"

        extractor = RefExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.branch_name == "main"
        assert result.is_default_branch is True
        mock_github_api.get_default_branch.assert_called_once_with("owner/repo")

    def test_extract_branch_api_detection_not_default(self, mock_config, mock_github_api):
        """Test API detection when branch is not default."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "develop"
        mock_config.GITHUB_TOKEN = "test-token"
        mock_github_api.get_default_branch.return_value = "main"

        extractor = RefExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.branch_name == "develop"
        assert result.is_default_branch is False

    def test_extract_branch_api_detection_failure(self, mock_config, mock_github_api):
        """Test API detection failure is handled gracefully."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "main"
        mock_config.GITHUB_TOKEN = "test-token"
        mock_github_api.get_default_branch.side_effect = Exception("API error")

        extractor = RefExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.branch_name == "main"
        assert result.is_default_branch is False  # Falls back to False on error

    def test_extract_branch_api_no_token(self, mock_config, mock_github_api):
        """Test that API is not called without token."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "main"
        mock_config.GITHUB_TOKEN = None

        extractor = RefExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.branch_name == "main"
        assert result.is_default_branch is False
        mock_github_api.get_default_branch.assert_not_called()

    def test_extract_tag(self, mock_config):
        """Test extraction for tag."""
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "v1.0.0"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name is None
        assert result.tag_name == "v1.0.0"
        assert result.is_main_branch is False
        assert result.is_default_branch is False

    def test_extract_tag_non_version(self, mock_config):
        """Test extraction for non-version tag."""
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "release-candidate"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name is None
        assert result.tag_name == "release-candidate"
        assert result.is_main_branch is False

    def test_extract_no_ref_name(self, mock_config):
        """Test extraction with no ref name."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = None

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name is None
        assert result.tag_name is None
        assert result.is_main_branch is False
        assert result.is_default_branch is False

    def test_extract_empty_ref_name(self, mock_config):
        """Test extraction with empty ref name."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = ""

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name is None
        assert result.tag_name is None

    def test_extract_with_head_ref_for_pr(self, mock_config):
        """Test extraction with HEAD_REF for pull request."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = None
        mock_config.GITHUB_HEAD_REF = "feature/pr-branch"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name is None  # HEAD_REF doesn't set branch_name
        # HEAD_REF is just logged for context

    def test_extract_unknown_ref_type(self, mock_config):
        """Test extraction with unknown ref type."""
        mock_config.GITHUB_REF_TYPE = "unknown"
        mock_config.GITHUB_REF_NAME = "something"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name is None
        assert result.tag_name is None

    def test_extract_branch_with_slashes(self, mock_config):
        """Test extraction for branch with slashes."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "feature/sub-feature/implementation"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name == "feature/sub-feature/implementation"
        assert result.is_main_branch is False

    def test_extract_branch_with_special_chars(self, mock_config):
        """Test extraction for branch with special characters."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "fix/bug-123_hotfix"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name == "fix/bug-123_hotfix"

    def test_extract_tag_with_special_chars(self, mock_config):
        """Test extraction for tag with special characters."""
        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "v1.0.0-beta.1+build.123"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.tag_name == "v1.0.0-beta.1+build.123"

    def test_check_default_branch_config_takes_precedence(self, mock_config, mock_github_api):
        """Test that DEFAULT_BRANCH config takes precedence over API."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "develop"
        mock_config.DEFAULT_BRANCH = "develop"
        mock_config.GITHUB_TOKEN = "test-token"
        mock_github_api.get_default_branch.return_value = "main"

        extractor = RefExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        # Config should take precedence, API should not be called
        assert result.is_default_branch is True
        mock_github_api.get_default_branch.assert_not_called()

    def test_main_branch_detection_case_sensitive(self, mock_config):
        """Test that main branch detection is case-sensitive."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "Main"  # Capital M

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.branch_name == "Main"
        assert result.is_main_branch is False  # Not 'main' or 'master'

    def test_default_branch_detection_case_sensitive(self, mock_config):
        """Test that default branch detection is case-sensitive."""
        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "Main"
        mock_config.DEFAULT_BRANCH = "main"

        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        assert result.is_default_branch is False  # Case doesn't match

    def test_logging_branch_output(self, mock_config, caplog):
        """Test logging for branch extraction."""
        import logging

        caplog.set_level(logging.INFO)

        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "feature/test"
        mock_config.DEBUG_MODE = True

        extractor = RefExtractor(mock_config)
        _ = extractor.extract()

        assert "Branch: feature/test" in caplog.text

    def test_logging_tag_output(self, mock_config, caplog):
        """Test logging for tag extraction."""
        import logging

        caplog.set_level(logging.INFO)

        mock_config.GITHUB_REF_TYPE = "tag"
        mock_config.GITHUB_REF_NAME = "v1.0.0"
        mock_config.DEBUG_MODE = True

        extractor = RefExtractor(mock_config)
        _ = extractor.extract()

        assert "Tag: v1.0.0" in caplog.text

    def test_logging_main_branch_detection(self, mock_config, caplog):
        """Test logging for main branch detection."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "main"
        mock_config.DEBUG_MODE = True

        extractor = RefExtractor(mock_config)
        _ = extractor.extract()

        # This is a debug message, should be logged when DEBUG_MODE is True
        assert "Detected main branch" in caplog.text or "Branch: main" in caplog.text

    def test_logging_default_branch_from_config(self, mock_config, caplog):
        """Test logging for default branch from config."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "main"
        mock_config.DEFAULT_BRANCH = "main"
        mock_config.DEBUG_MODE = True

        extractor = RefExtractor(mock_config)
        _ = extractor.extract()

        # This is a debug message
        assert "Branch" in caplog.text and "main" in caplog.text

    def test_logging_api_detection(self, mock_config, mock_github_api, caplog):
        """Test logging for API-based default branch detection."""
        import logging

        caplog.set_level(logging.INFO)

        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "main"
        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.DEBUG_MODE = True

        extractor = RefExtractor(mock_config, github_api=mock_github_api)
        _ = extractor.extract()

        # Should log that branch is default
        assert "Branch is the default branch: main" in caplog.text

    def test_logging_api_failure(self, mock_config, mock_github_api, caplog):
        """Test logging when API detection fails."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.GITHUB_REF_TYPE = "branch"
        mock_config.GITHUB_REF_NAME = "main"
        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.DEBUG_MODE = True
        mock_github_api.get_default_branch.side_effect = Exception("API error")

        extractor = RefExtractor(mock_config, github_api=mock_github_api)
        _ = extractor.extract()

        # Debug message about failure
        assert "Branch: main" in caplog.text or "default branch" in caplog.text

    def test_ref_metadata_model_compliance(self, mock_config):
        """Test that extracted data complies with RefMetadata model."""
        extractor = RefExtractor(mock_config)
        result = extractor.extract()

        # Verify model fields exist
        assert hasattr(result, "branch_name")
        assert hasattr(result, "tag_name")
        assert hasattr(result, "is_default_branch")
        assert hasattr(result, "is_main_branch")

        # Verify types
        assert isinstance(result.branch_name, str) or result.branch_name is None
        assert isinstance(result.tag_name, str) or result.tag_name is None
        assert isinstance(result.is_default_branch, bool)
        assert isinstance(result.is_main_branch, bool)
