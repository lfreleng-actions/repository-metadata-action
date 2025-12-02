# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for RepositoryExtractor.
"""

from unittest.mock import Mock

import pytest

from src.extractors.repository import RepositoryExtractor
from src.models import RepositoryMetadata


@pytest.fixture
def mock_config():
    """Create a mock config object."""
    config = Mock()
    config.GITHUB_REPOSITORY = "owner/repo"
    config.GITHUB_REPOSITORY_OWNER = "owner"
    config.REPO_VISIBILITY = None
    config.GITHUB_TOKEN = None
    config.GITHUB_RUN_ID = "12345"
    config.GITHUB_WORKFLOW = "CI"
    config.DEBUG_MODE = False
    return config


@pytest.fixture
def mock_github_api():
    """Create a mock GitHub API client."""
    api = Mock()
    repo_data = Mock()
    repo_data.private = False
    api.get_repository = Mock(return_value=repo_data)
    return api


class TestRepositoryExtractor:
    """Test suite for RepositoryExtractor."""

    def test_extract_basic_repository_info(self, mock_config):
        """Test extraction of basic repository information."""
        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        assert isinstance(result, RepositoryMetadata)
        assert result.owner == "owner"
        assert result.name == "repo"
        assert result.full_name == "owner/repo"
        assert result.is_public is False
        assert result.is_private is False

    def test_extract_with_visibility_public(self, mock_config):
        """Test extraction with public repository visibility."""
        mock_config.REPO_VISIBILITY = "public"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        assert result.owner == "owner"
        assert result.name == "repo"
        assert result.full_name == "owner/repo"
        assert result.is_public is True
        assert result.is_private is False

    def test_extract_with_visibility_private(self, mock_config):
        """Test extraction with private repository visibility."""
        mock_config.REPO_VISIBILITY = "private"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        assert result.is_public is False
        assert result.is_private is True

    def test_extract_with_visibility_internal(self, mock_config):
        """Test extraction with internal repository visibility."""
        mock_config.REPO_VISIBILITY = "internal"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        # Internal repos are treated as private for access control
        assert result.is_public is False
        assert result.is_private is True

    def test_extract_with_visibility_uppercase(self, mock_config):
        """Test extraction with uppercase visibility value."""
        mock_config.REPO_VISIBILITY = "PUBLIC"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        # Should be case-insensitive
        assert result.is_public is True
        assert result.is_private is False

    def test_extract_with_visibility_mixed_case(self, mock_config):
        """Test extraction with mixed case visibility value."""
        mock_config.REPO_VISIBILITY = "Private"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        assert result.is_public is False
        assert result.is_private is True

    def test_extract_with_api_public_repo(self, mock_config, mock_github_api):
        """Test extraction using API for public repository."""
        mock_config.GITHUB_TOKEN = "test-token"
        repo_data = Mock()
        repo_data.private = False
        mock_github_api.get_repository.return_value = repo_data

        extractor = RepositoryExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.is_public is True
        assert result.is_private is False
        mock_github_api.get_repository.assert_called_once_with("owner/repo")

    def test_extract_with_api_private_repo(self, mock_config, mock_github_api):
        """Test extraction using API for private repository."""
        mock_config.GITHUB_TOKEN = "test-token"
        repo_data = Mock()
        repo_data.private = True
        mock_github_api.get_repository.return_value = repo_data

        extractor = RepositoryExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.is_public is False
        assert result.is_private is True

    def test_extract_api_not_called_without_token(self, mock_config, mock_github_api):
        """Test that API is not called without token."""
        mock_config.GITHUB_TOKEN = None

        extractor = RepositoryExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        mock_github_api.get_repository.assert_not_called()
        assert result.is_public is False
        assert result.is_private is False

    def test_extract_visibility_config_takes_precedence(self, mock_config, mock_github_api):
        """Test that REPO_VISIBILITY config takes precedence over API."""
        mock_config.REPO_VISIBILITY = "private"
        mock_config.GITHUB_TOKEN = "test-token"
        repo_data = Mock()
        repo_data.private = False  # API says public
        mock_github_api.get_repository.return_value = repo_data

        extractor = RepositoryExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        # Config should take precedence, API should not be called
        assert result.is_private is True
        assert result.is_public is False
        mock_github_api.get_repository.assert_not_called()

    def test_extract_api_failure_handled(self, mock_config, mock_github_api):
        """Test that API failure is handled gracefully."""
        mock_config.GITHUB_TOKEN = "test-token"
        mock_github_api.get_repository.side_effect = Exception("API error")

        extractor = RepositoryExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        # Should not crash, falls back to False
        assert result.is_public is False
        assert result.is_private is False
        assert result.owner == "owner"
        assert result.name == "repo"

    def test_extract_repo_name_parsing_standard(self, mock_config):
        """Test standard repository name parsing."""
        mock_config.GITHUB_REPOSITORY = "octocat/Hello-World"
        mock_config.GITHUB_REPOSITORY_OWNER = "octocat"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        assert result.owner == "octocat"
        assert result.name == "Hello-World"
        assert result.full_name == "octocat/Hello-World"

    def test_extract_repo_name_parsing_with_dashes(self, mock_config):
        """Test repository name parsing with dashes."""
        mock_config.GITHUB_REPOSITORY = "my-org/my-repo-name"
        mock_config.GITHUB_REPOSITORY_OWNER = "my-org"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        assert result.owner == "my-org"
        assert result.name == "my-repo-name"
        assert result.full_name == "my-org/my-repo-name"

    def test_extract_repo_name_parsing_with_underscores(self, mock_config):
        """Test repository name parsing with underscores."""
        mock_config.GITHUB_REPOSITORY = "my_org/my_repo"
        mock_config.GITHUB_REPOSITORY_OWNER = "my_org"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        assert result.owner == "my_org"
        assert result.name == "my_repo"

    def test_extract_repo_name_parsing_with_dots(self, mock_config):
        """Test repository name parsing with dots."""
        mock_config.GITHUB_REPOSITORY = "organization/repo.name"
        mock_config.GITHUB_REPOSITORY_OWNER = "organization"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "repo.name"

    def test_extract_repo_name_fallback_parsing(self, mock_config):
        """Test fallback repository name parsing when owner doesn't match."""
        mock_config.GITHUB_REPOSITORY = "actual-owner/repo-name"
        mock_config.GITHUB_REPOSITORY_OWNER = "different-owner"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        # Should still extract name correctly using fallback logic
        assert result.owner == "different-owner"
        assert result.name == "repo-name"
        assert result.full_name == "actual-owner/repo-name"

    def test_extract_repo_name_no_slash(self, mock_config):
        """Test repository name when full name has no slash."""
        mock_config.GITHUB_REPOSITORY = "standalone-repo"
        mock_config.GITHUB_REPOSITORY_OWNER = "owner"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        # Fallback should use the full name as repo name
        assert result.owner == "owner"
        assert result.name == "standalone-repo"
        assert result.full_name == "standalone-repo"

    def test_extract_long_repo_name(self, mock_config):
        """Test extraction with very long repository name."""
        long_name = "a" * 100
        mock_config.GITHUB_REPOSITORY = f"owner/{long_name}"
        mock_config.GITHUB_REPOSITORY_OWNER = "owner"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        assert result.name == long_name

    def test_extract_long_owner_name(self, mock_config):
        """Test extraction with very long owner name."""
        long_owner = "o" * 100
        mock_config.GITHUB_REPOSITORY = f"{long_owner}/repo"
        mock_config.GITHUB_REPOSITORY_OWNER = long_owner

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        assert result.owner == long_owner
        assert result.name == "repo"

    def test_extract_with_multiple_slashes(self, mock_config):
        """Test extraction when repository name contains slashes (unusual)."""
        mock_config.GITHUB_REPOSITORY = "owner/repo/extra"
        mock_config.GITHUB_REPOSITORY_OWNER = "owner"

        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        # Should take everything after first slash
        assert result.owner == "owner"
        assert result.name == "repo/extra"

    def test_logging_output(self, mock_config, caplog):
        """Test that appropriate logging messages are generated."""
        import logging

        caplog.set_level(logging.INFO)

        mock_config.REPO_VISIBILITY = "public"
        mock_config.DEBUG_MODE = True

        extractor = RepositoryExtractor(mock_config)
        _ = extractor.extract()

        assert "Repository: owner/repo (public=True, private=False)" in caplog.text

    def test_logging_visibility_from_context(self, mock_config, caplog):
        """Test logging when visibility comes from context."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.REPO_VISIBILITY = "internal"
        mock_config.DEBUG_MODE = True

        extractor = RepositoryExtractor(mock_config)
        _ = extractor.extract()

        assert "Repository visibility from context: internal" in caplog.text

    def test_logging_visibility_from_api(self, mock_config, mock_github_api, caplog):
        """Test logging when visibility comes from API."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.DEBUG_MODE = True
        repo_data = Mock()
        repo_data.private = True
        mock_github_api.get_repository.return_value = repo_data

        extractor = RepositoryExtractor(mock_config, github_api=mock_github_api)
        _ = extractor.extract()

        assert "Fetching repository visibility from GitHub API" in caplog.text
        assert "Repository visibility from API: public=False, private=True" in caplog.text

    def test_logging_api_failure(self, mock_config, mock_github_api, caplog):
        """Test logging when API call fails."""
        import logging

        caplog.set_level(logging.WARNING)

        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.DEBUG_MODE = True
        mock_github_api.get_repository.side_effect = Exception("Network error")

        extractor = RepositoryExtractor(mock_config, github_api=mock_github_api)
        _ = extractor.extract()

        assert "Failed to fetch repository visibility from API" in caplog.text

    def test_logging_no_visibility_available(self, mock_config, caplog):
        """Test logging when no visibility information is available."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.DEBUG_MODE = True

        extractor = RepositoryExtractor(mock_config)
        _ = extractor.extract()

        assert (
            "Repository visibility not available (no REPO_VISIBILITY or API access)" in caplog.text
        )

    def test_repository_metadata_model_compliance(self, mock_config):
        """Test that extracted data complies with RepositoryMetadata model."""
        extractor = RepositoryExtractor(mock_config)
        result = extractor.extract()

        # Verify model fields exist
        assert hasattr(result, "owner")
        assert hasattr(result, "name")
        assert hasattr(result, "full_name")
        assert hasattr(result, "is_public")
        assert hasattr(result, "is_private")

        # Verify types
        assert isinstance(result.owner, str)
        assert isinstance(result.name, str)
        assert isinstance(result.full_name, str)
        assert isinstance(result.is_public, bool)
        assert isinstance(result.is_private, bool)

    def test_extract_no_api_provided(self, mock_config):
        """Test extraction when no API client is provided."""
        extractor = RepositoryExtractor(mock_config, github_api=None)
        result = extractor.extract()

        assert result.owner == "owner"
        assert result.name == "repo"
        assert result.is_public is False
        assert result.is_private is False

    def test_extract_mutually_exclusive_flags(self, mock_config):
        """Test that is_public and is_private are mutually exclusive."""
        test_cases = [
            ("public", True, False),
            ("private", False, True),
            ("internal", False, True),
        ]

        for visibility, expected_public, expected_private in test_cases:
            mock_config.REPO_VISIBILITY = visibility
            extractor = RepositoryExtractor(mock_config)
            result = extractor.extract()

            assert result.is_public == expected_public
            assert result.is_private == expected_private
            # Should never be both true
            assert not (result.is_public and result.is_private)
