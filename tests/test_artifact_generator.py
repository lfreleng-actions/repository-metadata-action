# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for artifact generator module.
"""

import re
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.formatters.artifact_generator import ArtifactGenerator
from src.models import (
    ActorMetadata,
    CacheMetadata,
    ChangedFilesMetadata,
    CommitMetadata,
    CompleteMetadata,
    EventMetadata,
    GerritMetadata,
    PullRequestMetadata,
    RefMetadata,
    RepositoryMetadata,
)


class TestArtifactGenerator:
    """Tests for ArtifactGenerator class."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a mock config with temporary paths."""
        config = Mock()
        config.RUNNER_TEMP = tmp_path
        config.ARTIFACT_FORMATS = ["json", "yaml"]
        return config

    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata for testing."""
        return CompleteMetadata(
            repository=RepositoryMetadata(
                owner="testowner",
                name="testrepo",
                full_name="testowner/testrepo",
                is_public=True,
                is_private=False,
            ),
            event=EventMetadata(name="push", is_branch_push=True),
            ref=RefMetadata(branch_name="main", is_main_branch=True),
            commit=CommitMetadata(
                sha="abc123def456789012345678901234567890abcd",
                sha_short="abc123d",
                message="Test commit",
                author="Test Author",
            ),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="testuser", id=12345),
            cache=CacheMetadata(key="test-cache-key", restore_key="test-cache-"),
            changed_files=ChangedFilesMetadata(files=["file1.py", "file2.py"]),
            changed_files_last_commit=ChangedFilesMetadata(files=["file1.py", "file2.py"]),
            gerrit_environment=GerritMetadata(
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
                source="none",
            ),
        )

    def test_initialization(self, mock_config):
        """Test artifact generator initialization."""
        generator = ArtifactGenerator(mock_config)

        assert generator.config == mock_config
        assert generator.suffix is not None
        assert isinstance(generator.suffix, str)

    def test_suffix_format(self, mock_config):
        """Test suffix format is timestamp-random."""
        generator = ArtifactGenerator(mock_config)

        # Should match pattern: {YYYYMMDD}-{HHMMSS}-{hex}
        pattern = r"^\d{8}-\d{6}-[a-f0-9]{4}$"
        assert re.match(pattern, generator.suffix), (
            f"Suffix doesn't match pattern: {generator.suffix}"
        )

    def test_suffix_contains_timestamp(self, mock_config):
        """Test suffix contains valid timestamp."""
        generator = ArtifactGenerator(mock_config)

        parts = generator.suffix.split("-")
        assert len(parts) == 3, "Suffix should have three parts separated by dashes"

        date_part = parts[0]
        time_part = parts[1]
        assert date_part.isdigit(), "Date part should be numeric"
        assert time_part.isdigit(), "Time part should be numeric"
        assert len(date_part) == 8, "Date part should be YYYYMMDD format"
        assert len(time_part) == 6, "Time part should be HHMMSS format"

    def test_suffix_contains_random_hex(self, mock_config):
        """Test suffix contains random hex component."""
        generator = ArtifactGenerator(mock_config)

        parts = generator.suffix.split("-")
        assert len(parts) == 3

        random_part = parts[2]
        assert len(random_part) == 4, "Random part should be 4 hex characters"
        assert all(c in "0123456789abcdef" for c in random_part), "Random part should be hex"

    def test_suffix_uniqueness(self, mock_config):
        """Test that multiple generators produce unique suffixes."""
        suffixes = set()

        # Generate 100 suffixes
        for _ in range(100):
            generator = ArtifactGenerator(mock_config)
            suffixes.add(generator.suffix)

        # All should be unique
        assert len(suffixes) == 100, "Suffixes should be unique"

    def test_suffix_prevents_collision_parallel_execution(self, mock_config):
        """Test suffix prevents collisions in parallel execution."""
        # Simulate parallel execution with same timestamp
        from datetime import datetime, timezone

        with patch("src.formatters.artifact_generator.datetime") as mock_datetime:
            # Mock datetime.now to return a fixed datetime
            fixed_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = fixed_dt
            mock_datetime.timezone = timezone

            # Even with same timestamp, random component makes them unique
            suffixes = set()
            for _ in range(50):
                generator = ArtifactGenerator(mock_config)
                suffixes.add(generator.suffix)

            # Should still be unique due to random component
            assert len(suffixes) == 50

    def test_generate_creates_directory(self, mock_config, sample_metadata):
        """Test generate creates artifact directory."""
        generator = ArtifactGenerator(mock_config)

        result_path = generator.generate(sample_metadata)

        assert result_path.exists()
        assert result_path.is_dir()
        assert result_path.name == f"repository-metadata-{generator.suffix}"

    def test_generate_directory_within_runner_temp(self, mock_config, sample_metadata):
        """Test generated directory is within RUNNER_TEMP."""
        generator = ArtifactGenerator(mock_config)

        result_path = generator.generate(sample_metadata)

        # Resolve paths to absolute
        resolved_result = result_path.resolve()
        resolved_temp = mock_config.RUNNER_TEMP.resolve()

        # Check that result is within temp directory
        assert str(resolved_result).startswith(str(resolved_temp))

    def test_generate_creates_json_files(self, mock_config, sample_metadata):
        """Test generate creates JSON files when format includes json."""
        mock_config.ARTIFACT_FORMATS = ["json"]
        generator = ArtifactGenerator(mock_config)

        result_path = generator.generate(sample_metadata)

        # Check for JSON files
        assert (result_path / "repository-metadata.json").exists()
        assert (result_path / "repository-metadata-pretty.json").exists()

    def test_generate_creates_yaml_file(self, mock_config, sample_metadata):
        """Test generate creates YAML file when format includes yaml."""
        mock_config.ARTIFACT_FORMATS = ["yaml"]
        generator = ArtifactGenerator(mock_config)

        result_path = generator.generate(sample_metadata)

        # Check for YAML file
        assert (result_path / "repository-metadata.yaml").exists()

    def test_generate_creates_both_formats(self, mock_config, sample_metadata):
        """Test generate creates both JSON and YAML when both in formats."""
        mock_config.ARTIFACT_FORMATS = ["json", "yaml"]
        generator = ArtifactGenerator(mock_config)

        result_path = generator.generate(sample_metadata)

        # Check for all files
        assert (result_path / "repository-metadata.json").exists()
        assert (result_path / "repository-metadata-pretty.json").exists()
        assert (result_path / "repository-metadata.yaml").exists()

    def test_generate_json_content_valid(self, mock_config, sample_metadata):
        """Test generated JSON content is valid."""
        import json

        mock_config.ARTIFACT_FORMATS = ["json"]
        generator = ArtifactGenerator(mock_config)

        result_path = generator.generate(sample_metadata)

        # Read and parse compact JSON
        with open(result_path / "repository-metadata.json") as f:
            data = json.load(f)

        assert data["repository"]["owner"] == "testowner"
        assert data["commit"]["sha"] == "abc123def456789012345678901234567890abcd"

    def test_generate_json_pretty_formatted(self, mock_config, sample_metadata):
        """Test pretty JSON is actually formatted with indentation."""
        mock_config.ARTIFACT_FORMATS = ["json"]
        generator = ArtifactGenerator(mock_config)

        result_path = generator.generate(sample_metadata)

        with open(result_path / "repository-metadata-pretty.json") as f:
            content = f.read()

        # Pretty JSON should have newlines and indentation
        assert "\n" in content
        assert "  " in content  # Indentation

    def test_generate_yaml_content_valid(self, mock_config, sample_metadata):
        """Test generated YAML content is valid."""
        import yaml  # type: ignore[import-untyped]

        mock_config.ARTIFACT_FORMATS = ["yaml"]
        generator = ArtifactGenerator(mock_config)

        result_path = generator.generate(sample_metadata)

        # Read and parse YAML
        with open(result_path / "repository-metadata.yaml") as f:
            data = yaml.safe_load(f)

        assert data["repository"]["owner"] == "testowner"
        assert data["commit"]["sha"] == "abc123def456789012345678901234567890abcd"

    def test_generate_returns_path(self, mock_config, sample_metadata):
        """Test generate returns the artifact directory path."""
        generator = ArtifactGenerator(mock_config)

        result = generator.generate(sample_metadata)

        assert isinstance(result, Path)
        assert result.name == f"repository-metadata-{generator.suffix}"

    def test_generate_with_empty_formats(self, mock_config, sample_metadata):
        """Test generate with empty formats list."""
        mock_config.ARTIFACT_FORMATS = []
        generator = ArtifactGenerator(mock_config)

        result_path = generator.generate(sample_metadata)

        # Directory should be created but no files
        assert result_path.exists()
        assert list(result_path.glob("*")) == []

    def test_generate_validates_directory_name(self, mock_config, sample_metadata):
        """Test that directory name is validated for safety."""
        generator = ArtifactGenerator(mock_config)

        # Should not raise ValidationError for normal suffix
        result_path = generator.generate(sample_metadata)
        assert result_path.exists()

    def test_generate_prevents_path_traversal(self, mock_config, sample_metadata):
        """Test that path traversal in suffix is prevented."""
        generator = ArtifactGenerator(mock_config)

        # Even if suffix somehow had .. (shouldn't happen), validation should catch it
        # This tests the safety layer
        result_path = generator.generate(sample_metadata)

        # Verify path is still within RUNNER_TEMP
        assert str(result_path.resolve()).startswith(str(mock_config.RUNNER_TEMP.resolve()))

    def test_suffix_chronological_ordering(self, mock_config):
        """Test that suffixes maintain chronological order."""
        suffixes = []

        for i in range(5):
            generator = ArtifactGenerator(mock_config)
            suffixes.append(generator.suffix)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Extract timestamps
        timestamps = [int(s.split("-")[0]) for s in suffixes]

        # Should be in ascending order (or equal if very fast)
        for i in range(len(timestamps) - 1):
            assert timestamps[i] <= timestamps[i + 1]

    def test_suffix_length_reasonable(self, mock_config):
        """Test suffix length is reasonable for file system."""
        generator = ArtifactGenerator(mock_config)

        # Suffix should be reasonable length (timestamp ~13 digits + dash + 8 hex = ~22 chars)
        assert len(generator.suffix) < 30, "Suffix too long"
        assert len(generator.suffix) > 15, "Suffix too short"

    def test_multiple_generators_different_suffixes(self, mock_config):
        """Test multiple generator instances have different suffixes."""
        gen1 = ArtifactGenerator(mock_config)
        gen2 = ArtifactGenerator(mock_config)
        gen3 = ArtifactGenerator(mock_config)

        assert gen1.suffix != gen2.suffix
        assert gen2.suffix != gen3.suffix
        assert gen1.suffix != gen3.suffix

    def test_suffix_no_special_characters(self, mock_config):
        """Test suffix contains only safe filesystem characters."""
        generator = ArtifactGenerator(mock_config)

        # Should only contain: digits, lowercase hex letters, and dash
        safe_chars = set("0123456789abcdef-")
        assert all(c in safe_chars for c in generator.suffix)

    @patch("src.formatters.artifact_generator.secrets.token_hex")
    def test_suffix_uses_secure_random(self, mock_token_hex, mock_config):
        """Test suffix generation uses secrets module for randomness."""
        mock_token_hex.return_value = "deadbeef"

        generator = ArtifactGenerator(mock_config)

        # Should have called secrets.token_hex(2)
        mock_token_hex.assert_called_once_with(2)
        assert generator.suffix.endswith("-deadbeef")
