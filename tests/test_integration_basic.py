# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Basic integration tests to increase coverage.
Tests simple integrations and edge cases across modules.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.config import Config
from src.models import (
    ChangedFilesMetadata,
    RepositoryMetadata,
)
from src.validators import InputValidator


class TestConfigEdgeCases:
    """Test Config edge cases to improve coverage."""

    def test_config_with_all_optional_fields_none(self, monkeypatch):
        """Test config when all optional fields are None."""
        # Set only required fields
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "owner")
        monkeypatch.setenv("GITHUB_SHA", "a" * 40)
        monkeypatch.setenv("GITHUB_REF_NAME", "main")
        monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
        monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
        monkeypatch.setenv("GITHUB_ACTOR", "testuser")
        monkeypatch.setenv("GITHUB_WORKFLOW", "CI")
        monkeypatch.setenv("GITHUB_RUN_ID", "12345")
        monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
        monkeypatch.setenv("GITHUB_OUTPUT", "/tmp/github_output")

        # Clear optional fields
        for key in [
            "GITHUB_TOKEN",
            "GITHUB_EVENT_PATH",
            "GITHUB_HEAD_REF",
            "GITHUB_BASE_REF",
            "GITHUB_ACTOR_ID",
            "DEFAULT_BRANCH",
            "REPO_VISIBILITY",
            "PR_HEAD_REPO_FORK",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = Config()

        assert config.GITHUB_REPOSITORY == "owner/repo"
        assert config.GITHUB_TOKEN is None
        assert config.GITHUB_EVENT_PATH is None

    def test_config_with_git_fetch_depth_negative(self, monkeypatch):
        """Test config with negative git fetch depth falls back to default."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "owner")
        monkeypatch.setenv("GITHUB_SHA", "a" * 40)
        monkeypatch.setenv("GITHUB_REF_NAME", "main")
        monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
        monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
        monkeypatch.setenv("GITHUB_ACTOR", "testuser")
        monkeypatch.setenv("GITHUB_WORKFLOW", "CI")
        monkeypatch.setenv("GITHUB_RUN_ID", "12345")
        monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
        monkeypatch.setenv("GITHUB_OUTPUT", "/tmp/github_output")
        monkeypatch.setenv("GIT_FETCH_DEPTH", "-1")

        # Should default to 15 when validation fails
        config = Config()
        assert config.GIT_FETCH_DEPTH == 15

    def test_config_with_git_fetch_depth_zero(self, monkeypatch):
        """Test config with zero git fetch depth falls back to default."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "owner")
        monkeypatch.setenv("GITHUB_SHA", "a" * 40)
        monkeypatch.setenv("GITHUB_REF_NAME", "main")
        monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
        monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
        monkeypatch.setenv("GITHUB_ACTOR", "testuser")
        monkeypatch.setenv("GITHUB_WORKFLOW", "CI")
        monkeypatch.setenv("GITHUB_RUN_ID", "12345")
        monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
        monkeypatch.setenv("GITHUB_OUTPUT", "/tmp/github_output")
        monkeypatch.setenv("GIT_FETCH_DEPTH", "0")

        # Should default to 15 when validation fails
        config = Config()
        assert config.GIT_FETCH_DEPTH == 15

    def test_config_debug_mode_true(self, monkeypatch):
        """Test config with debug mode enabled."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "owner")
        monkeypatch.setenv("GITHUB_SHA", "a" * 40)
        monkeypatch.setenv("GITHUB_REF_NAME", "main")
        monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
        monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
        monkeypatch.setenv("GITHUB_ACTOR", "testuser")
        monkeypatch.setenv("GITHUB_WORKFLOW", "CI")
        monkeypatch.setenv("GITHUB_RUN_ID", "12345")
        monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
        monkeypatch.setenv("GITHUB_OUTPUT", "/tmp/github_output")
        monkeypatch.setenv("DEBUG_MODE", "true")

        config = Config()
        assert config.DEBUG_MODE is True

    def test_config_debug_mode_1(self, monkeypatch):
        """Test config with debug mode as '1'."""
        monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
        monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "owner")
        monkeypatch.setenv("GITHUB_SHA", "a" * 40)
        monkeypatch.setenv("GITHUB_REF_NAME", "main")
        monkeypatch.setenv("GITHUB_REF_TYPE", "branch")
        monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
        monkeypatch.setenv("GITHUB_ACTOR", "testuser")
        monkeypatch.setenv("GITHUB_WORKFLOW", "CI")
        monkeypatch.setenv("GITHUB_RUN_ID", "12345")
        monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
        monkeypatch.setenv("GITHUB_OUTPUT", "/tmp/github_output")
        monkeypatch.setenv("DEBUG_MODE", "1")

        config = Config()
        assert config.DEBUG_MODE is True


class TestValidatorEdgeCases:
    """Test validator edge cases."""

    def test_validate_sha_valid(self):
        """Test SHA validation with valid SHA."""
        result = InputValidator.validate_sha("a" * 40, "test")
        assert result == "a" * 40

    def test_validate_actor_name_valid(self):
        """Test actor name validation."""
        result = InputValidator.validate_actor_name("testuser")
        assert result == "testuser"

    def test_validate_ref_name_with_slashes(self):
        """Test ref name validation with slashes."""
        result = InputValidator.validate_ref_name("feature/branch", "test")
        assert result == "feature/branch"


class TestModelEdgeCases:
    """Test model edge cases."""

    def test_repository_metadata_all_fields(self):
        """Test RepositoryMetadata with all fields populated."""
        metadata = RepositoryMetadata(
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            is_public=True,
            is_private=False,
        )

        assert metadata.owner == "test-owner"
        assert metadata.name == "test-repo"
        assert metadata.full_name == "test-owner/test-repo"
        assert metadata.is_public is True
        assert metadata.is_private is False

    def test_repository_metadata_dict_conversion(self):
        """Test RepositoryMetadata to dict conversion."""
        metadata = RepositoryMetadata(
            owner="owner", name="repo", full_name="owner/repo", is_public=False, is_private=True
        )

        data = metadata.model_dump()
        assert data["owner"] == "owner"
        assert data["name"] == "repo"
        assert data["is_public"] is False
        assert data["is_private"] is True

    def test_changed_files_metadata_empty(self):
        """Test ChangedFilesMetadata with no files."""
        metadata = ChangedFilesMetadata(count=0, files=[])

        assert metadata.count == 0
        assert metadata.files == []
        assert len(metadata.files) == 0

    def test_changed_files_metadata_many_files(self):
        """Test ChangedFilesMetadata with many files."""
        files = [f"file{i}.py" for i in range(1000)]
        metadata = ChangedFilesMetadata(count=1000, files=files)

        assert metadata.count == 1000
        assert len(metadata.files) == 1000
        assert metadata.files[0] == "file0.py"
        assert metadata.files[999] == "file999.py"

    def test_changed_files_metadata_unicode_files(self):
        """Test ChangedFilesMetadata with unicode filenames."""
        files = ["文件.py", "ファイル.js", "файл.md"]
        metadata = ChangedFilesMetadata(count=3, files=files)

        assert metadata.count == 3
        assert all(f in metadata.files for f in files)


class TestArtifactGeneratorEdgeCases:
    """Test artifact generator edge cases."""

    def test_artifact_suffix_uniqueness(self):
        """Test that artifact suffixes are unique across multiple generations."""
        import time
        from unittest.mock import Mock

        from src.formatters.artifact_generator import ArtifactGenerator

        config = Mock()
        config.GITHUB_WORKFLOW = "test-workflow"
        config.GITHUB_RUN_ID = "12345"

        # Generate multiple suffixes and check they're unique
        suffixes = set()
        for _ in range(5):
            gen = ArtifactGenerator(config)
            suffixes.add(gen.suffix)
            time.sleep(0.001)  # Small delay to ensure timestamp changes

        # All suffixes should be unique
        assert len(suffixes) == 5

    def test_artifact_suffix_format(self):
        """Test artifact suffix format."""
        from unittest.mock import Mock

        from src.formatters.artifact_generator import ArtifactGenerator

        config = Mock()
        config.GITHUB_WORKFLOW = "test-workflow"
        config.GITHUB_RUN_ID = "12345"

        gen = ArtifactGenerator(config)
        suffix = gen.suffix
        parts = suffix.split("-")

        # Suffix format is: {YYYYMMDD}-{HHMMSS}-{random_hex}
        assert len(parts) == 3
        # First part is date (YYYYMMDD)
        assert parts[0].isdigit()
        assert len(parts[0]) == 8
        # Second part is time (HHMMSS)
        assert parts[1].isdigit()
        assert len(parts[1]) == 6
        # Third part is hex (4 chars)
        assert len(parts[2]) == 4
        assert all(c in "0123456789abcdef" for c in parts[2])


class TestGitOperationsEdgeCases:
    """Test git operations edge cases."""

    def test_git_operations_initialization(self):
        """Test git operations initialization."""
        from src.git_operations import GitOperations

        git_ops = GitOperations()

        # Should have a repo_path
        assert git_ops.repo_path is not None
        assert isinstance(git_ops.repo_path, Path)

    def test_git_operations_has_git_repo_false(self):
        """Test has_git_repo returns False when no repo."""
        from src.git_operations import GitOperations

        with tempfile.TemporaryDirectory() as tmpdir:
            git_ops = GitOperations(repo_path=Path(tmpdir))
            assert git_ops.has_git_repo() is False


class TestBaseExtractorErrorHandling:
    """Test BaseExtractor error handling."""

    def test_base_extractor_error_with_exception(self):
        """Test error method with exception."""
        from src.extractors.base import BaseExtractor

        config = Mock()
        config.DEBUG_MODE = False

        class TestExtractor(BaseExtractor):
            def extract(self):
                pass

        extractor = TestExtractor(config)

        # Should not raise
        try:
            extractor.error("Test error", Exception("test"))
        except Exception:
            pytest.fail("error() should not raise")

    def test_base_extractor_error_without_exception(self):
        """Test error method without exception."""
        from src.extractors.base import BaseExtractor

        config = Mock()
        config.DEBUG_MODE = False

        class TestExtractor(BaseExtractor):
            def extract(self):
                pass

        extractor = TestExtractor(config)

        # Should not raise
        try:
            extractor.error("Test error")
        except Exception:
            pytest.fail("error() should not raise")
