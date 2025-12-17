# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for CacheExtractor.
"""

from unittest.mock import Mock

import pytest

from src.extractors.cache import CacheExtractor
from src.models import CacheMetadata


@pytest.fixture
def mock_config():
    """Create a mock config object."""
    config = Mock()
    config.GITHUB_REPOSITORY = "owner/repo"
    config.GITHUB_REPOSITORY_OWNER = "owner"
    config.GITHUB_REF_NAME = "main"
    config.GITHUB_SHA = "abc123def456"
    config.GITHUB_RUN_ID = "12345"
    config.GITHUB_WORKFLOW = "CI"
    config.DEBUG_MODE = False
    return config


class TestCacheExtractor:
    """Test suite for CacheExtractor."""

    def test_extract_basic_cache_keys(self, mock_config):
        """Test extraction of basic cache keys."""
        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert isinstance(result, CacheMetadata)
        assert result.key == "owner-repo-main-abc123def456"
        assert result.restore_key == "owner-repo-main-"

    def test_extract_with_feature_branch(self, mock_config):
        """Test cache key generation for feature branch."""
        mock_config.GITHUB_REF_NAME = "feature/new-feature"

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert result.key == "owner-repo-feature/new-feature-abc123def456"
        assert result.restore_key == "owner-repo-feature/new-feature-"

    def test_extract_with_tag(self, mock_config):
        """Test cache key generation for tag."""
        mock_config.GITHUB_REF_NAME = "v1.0.0"

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert result.key == "owner-repo-v1.0.0-abc123def456"
        assert result.restore_key == "owner-repo-v1.0.0-"

    def test_extract_with_different_sha(self, mock_config):
        """Test that different SHAs produce different cache keys."""
        extractor1 = CacheExtractor(mock_config)
        result1 = extractor1.extract()

        mock_config.GITHUB_SHA = "different123"
        extractor2 = CacheExtractor(mock_config)
        result2 = extractor2.extract()

        assert result1.key != result2.key
        assert result1.restore_key == result2.restore_key  # Same prefix

    def test_extract_with_different_branch(self, mock_config):
        """Test that different branches produce different cache keys."""
        extractor1 = CacheExtractor(mock_config)
        result1 = extractor1.extract()

        mock_config.GITHUB_REF_NAME = "develop"
        extractor2 = CacheExtractor(mock_config)
        result2 = extractor2.extract()

        assert result1.key != result2.key
        assert result1.restore_key != result2.restore_key

    def test_extract_with_different_repo(self, mock_config):
        """Test that different repos produce different cache keys."""
        extractor1 = CacheExtractor(mock_config)
        result1 = extractor1.extract()

        mock_config.GITHUB_REPOSITORY = "owner/different-repo"
        extractor2 = CacheExtractor(mock_config)
        result2 = extractor2.extract()

        assert result1.key != result2.key
        assert result1.restore_key != result2.restore_key

    def test_extract_with_different_owner(self, mock_config):
        """Test that different owners produce different cache keys."""
        extractor1 = CacheExtractor(mock_config)
        result1 = extractor1.extract()

        mock_config.GITHUB_REPOSITORY_OWNER = "different-owner"
        mock_config.GITHUB_REPOSITORY = "different-owner/repo"
        extractor2 = CacheExtractor(mock_config)
        result2 = extractor2.extract()

        assert result1.key != result2.key
        assert result1.restore_key != result2.restore_key

    def test_extract_repo_name_parsing(self, mock_config):
        """Test correct parsing of repository name from full name."""
        mock_config.GITHUB_REPOSITORY = "my-org/my-repo"
        mock_config.GITHUB_REPOSITORY_OWNER = "my-org"

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert "my-org" in result.key
        assert "my-repo" in result.key
        assert result.key == "my-org-my-repo-main-abc123def456"

    def test_extract_with_no_ref_name(self, mock_config):
        """Test cache key generation when ref name is None."""
        mock_config.GITHUB_REF_NAME = None

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        # Should fallback to 'main'
        assert result.key == "owner-repo-main-abc123def456"
        assert result.restore_key == "owner-repo-main-"

    def test_extract_with_empty_ref_name(self, mock_config):
        """Test cache key generation when ref name is empty string."""
        mock_config.GITHUB_REF_NAME = ""

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        # Empty string is falsy, should fallback to 'main'
        assert result.key == "owner-repo-main-abc123def456"
        assert result.restore_key == "owner-repo-main-"

    def test_extract_with_long_sha(self, mock_config):
        """Test cache key generation with full 40-character SHA."""
        mock_config.GITHUB_SHA = "a" * 40

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert result.key.endswith("-" + "a" * 40)
        assert len(result.key.split("-")[-1]) == 40

    def test_extract_with_short_sha(self, mock_config):
        """Test cache key generation with short SHA."""
        mock_config.GITHUB_SHA = "abc123"

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert result.key == "owner-repo-main-abc123"
        assert result.restore_key == "owner-repo-main-"

    def test_extract_restore_key_format(self, mock_config):
        """Test that restore key is a proper prefix of cache key."""
        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        # Cache key should start with restore key
        assert result.key.startswith(result.restore_key)

        # Restore key should end with dash
        assert result.restore_key.endswith("-")

        # Cache key should have SHA after restore key
        suffix = result.key[len(result.restore_key) :]
        assert suffix == mock_config.GITHUB_SHA

    def test_extract_cache_key_components(self, mock_config):
        """Test that cache key contains all expected components."""
        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        parts = result.key.split("-")

        # Should have: owner, repo, ref, sha (4 parts minimum)
        assert len(parts) >= 4
        assert parts[0] == "owner"
        assert parts[1] == "repo"
        assert parts[2] == "main"
        assert parts[3] == "abc123def456"

    def test_extract_restore_key_components(self, mock_config):
        """Test that restore key contains expected components."""
        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        # Should be owner-repo-ref- (without SHA)
        assert result.restore_key == "owner-repo-main-"

        parts = result.restore_key.rstrip("-").split("-")
        assert len(parts) == 3
        assert parts[0] == "owner"
        assert parts[1] == "repo"
        assert parts[2] == "main"

    def test_extract_with_branch_containing_dashes(self, mock_config):
        """Test cache key with branch name containing dashes."""
        mock_config.GITHUB_REF_NAME = "feature-branch-name"

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert "feature-branch-name" in result.key
        assert "feature-branch-name" in result.restore_key

    def test_extract_with_branch_containing_slashes(self, mock_config):
        """Test cache key with branch name containing slashes."""
        mock_config.GITHUB_REF_NAME = "feature/sub/branch"

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        # Slashes should be preserved in key
        assert "feature/sub/branch" in result.key
        assert "feature/sub/branch" in result.restore_key

    def test_extract_with_repo_containing_dashes(self, mock_config):
        """Test cache key with repository name containing dashes."""
        mock_config.GITHUB_REPOSITORY = "my-owner/my-repo-name"
        mock_config.GITHUB_REPOSITORY_OWNER = "my-owner"

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert "my-owner" in result.key
        assert "my-repo-name" in result.key

    def test_extract_with_repo_containing_underscores(self, mock_config):
        """Test cache key with repository name containing underscores."""
        mock_config.GITHUB_REPOSITORY = "my_org/my_repo"
        mock_config.GITHUB_REPOSITORY_OWNER = "my_org"

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert "my_org" in result.key
        assert "my_repo" in result.key

    def test_extract_with_repo_containing_dots(self, mock_config):
        """Test cache key with repository name containing dots."""
        mock_config.GITHUB_REPOSITORY = "org/repo.name"
        mock_config.GITHUB_REPOSITORY_OWNER = "org"

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert "repo.name" in result.key

    def test_extract_deterministic(self, mock_config):
        """Test that cache key generation is deterministic."""
        extractor1 = CacheExtractor(mock_config)
        result1 = extractor1.extract()

        extractor2 = CacheExtractor(mock_config)
        result2 = extractor2.extract()

        assert result1.key == result2.key
        assert result1.restore_key == result2.restore_key

    def test_logging_output(self, mock_config, caplog):
        """Test that appropriate logging messages are generated."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.DEBUG_MODE = True

        extractor = CacheExtractor(mock_config)
        _ = extractor.extract()

        assert "Generating cache keys" in caplog.text
        assert "Cache key: owner-repo-main-abc123def456" in caplog.text
        assert "Cache restore key prefix: owner-repo-main-" in caplog.text

    def test_cache_metadata_model_compliance(self, mock_config):
        """Test that extracted data complies with CacheMetadata model."""
        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        # Verify model fields exist
        assert hasattr(result, "key")
        assert hasattr(result, "restore_key")

        # Verify types
        assert isinstance(result.key, str)
        assert isinstance(result.restore_key, str)

        # Verify non-empty
        assert len(result.key) > 0
        assert len(result.restore_key) > 0

    def test_extract_with_pr_branch(self, mock_config):
        """Test cache key generation for pull request branch."""
        mock_config.GITHUB_REF_NAME = "pr-123"

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert "pr-123" in result.key
        assert "pr-123" in result.restore_key

    def test_extract_with_release_branch(self, mock_config):
        """Test cache key generation for release branch."""
        mock_config.GITHUB_REF_NAME = "release/v1.0.0"

        extractor = CacheExtractor(mock_config)
        result = extractor.extract()

        assert "release/v1.0.0" in result.key
        assert "release/v1.0.0" in result.restore_key

    def test_extract_key_uniqueness(self, mock_config):
        """Test that cache keys are unique for different configurations."""
        configs = [
            ("owner/repo1", "main", "sha1"),
            ("owner/repo2", "main", "sha1"),
            ("owner/repo1", "develop", "sha1"),
            ("owner/repo1", "main", "sha2"),
        ]

        keys = set()
        for repo, ref, sha in configs:
            mock_config.GITHUB_REPOSITORY = repo
            mock_config.GITHUB_REF_NAME = ref
            mock_config.GITHUB_SHA = sha

            extractor = CacheExtractor(mock_config)
            result = extractor.extract()
            keys.add(result.key)

        # All keys should be unique
        assert len(keys) == len(configs)

    def test_extract_restore_key_sharing(self, mock_config):
        """Test that same branch shares restore key prefix."""
        mock_config.GITHUB_SHA = "sha1"
        extractor1 = CacheExtractor(mock_config)
        result1 = extractor1.extract()

        mock_config.GITHUB_SHA = "sha2"
        extractor2 = CacheExtractor(mock_config)
        result2 = extractor2.extract()

        # Different cache keys
        assert result1.key != result2.key

        # Same restore key prefix
        assert result1.restore_key == result2.restore_key
