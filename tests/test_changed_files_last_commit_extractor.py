# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for ChangedFilesLastCommitExtractor.
"""

from unittest.mock import Mock

import pytest

from src.extractors.changed_files_last_commit import ChangedFilesLastCommitExtractor
from src.models import ChangedFilesMetadata


class TestChangedFilesLastCommitExtractor:
    """Tests for ChangedFilesLastCommitExtractor class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock()
        config.GITHUB_SHA = "a" * 40
        return config

    @pytest.fixture
    def mock_git_ops(self):
        """Create a mock git operations handler."""
        git_ops = Mock()
        git_ops.has_git_repo.return_value = True
        return git_ops

    def test_initialization(self, mock_config, mock_git_ops):
        """Test extractor initialization."""
        extractor = ChangedFilesLastCommitExtractor(config=mock_config, git_ops=mock_git_ops)

        assert extractor.config == mock_config
        assert extractor.git_ops == mock_git_ops

    def test_extract_with_changed_files(self, mock_config, mock_git_ops):
        """Test extracting changed files from last commit."""
        # Setup mock git operations
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": ["new_file.py"],
            "modified": ["existing_file.py", "another_file.py"],
            "removed": ["old_file.py"],
        }

        extractor = ChangedFilesLastCommitExtractor(config=mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Verify git operations called correctly
        mock_git_ops.get_commit_files_categorized.assert_called_once_with("HEAD")

        # Verify result
        assert isinstance(result, ChangedFilesMetadata)
        assert result.count == 4
        assert result.added_count == 1
        assert result.modified_count == 2
        assert result.removed_count == 1
        assert "new_file.py" in result.added
        assert "existing_file.py" in result.modified
        assert "another_file.py" in result.modified
        assert "old_file.py" in result.removed
        assert len(result.files) == 4

    def test_extract_with_no_changed_files(self, mock_config, mock_git_ops):
        """Test extracting when no files changed in last commit."""
        # Setup mock git operations - empty changes
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": [],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesLastCommitExtractor(config=mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Verify result
        assert isinstance(result, ChangedFilesMetadata)
        assert result.count == 0
        assert result.added_count == 0
        assert result.modified_count == 0
        assert result.removed_count == 0
        assert len(result.files) == 0

    def test_extract_without_git_repo(self, mock_config):
        """Test extraction when git repository is not available."""
        # Create git_ops that returns False for has_git_repo
        mock_git_ops = Mock()
        mock_git_ops.has_git_repo.return_value = False

        extractor = ChangedFilesLastCommitExtractor(config=mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Should return empty metadata
        assert isinstance(result, ChangedFilesMetadata)
        assert result.count == 0
        assert len(result.files) == 0

        # get_commit_files_categorized should not be called
        mock_git_ops.get_commit_files_categorized.assert_not_called()

    def test_extract_without_git_ops(self, mock_config):
        """Test extraction when git_ops is None."""
        extractor = ChangedFilesLastCommitExtractor(config=mock_config, git_ops=None)
        result = extractor.extract()

        # Should return empty metadata
        assert isinstance(result, ChangedFilesMetadata)
        assert result.count == 0
        assert len(result.files) == 0

    def test_extract_with_git_error(self, mock_config, mock_git_ops):
        """Test extraction when git operations raise an exception."""
        # Setup mock to raise exception
        mock_git_ops.get_commit_files_categorized.side_effect = Exception("Git operation failed")

        extractor = ChangedFilesLastCommitExtractor(config=mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Should return empty metadata on failure
        assert isinstance(result, ChangedFilesMetadata)
        assert result.count == 0
        assert len(result.files) == 0

    def test_extract_only_added_files(self, mock_config, mock_git_ops):
        """Test extraction with only added files."""
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": ["file1.py", "file2.py", "file3.py"],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesLastCommitExtractor(config=mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 3
        assert result.added_count == 3
        assert result.modified_count == 0
        assert result.removed_count == 0

    def test_extract_only_modified_files(self, mock_config, mock_git_ops):
        """Test extraction with only modified files."""
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": [],
            "modified": ["file1.py", "file2.py"],
            "removed": [],
        }

        extractor = ChangedFilesLastCommitExtractor(config=mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 2
        assert result.added_count == 0
        assert result.modified_count == 2
        assert result.removed_count == 0

    def test_extract_only_removed_files(self, mock_config, mock_git_ops):
        """Test extraction with only removed files."""
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": [],
            "modified": [],
            "removed": ["file1.py"],
        }

        extractor = ChangedFilesLastCommitExtractor(config=mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 1
        assert result.added_count == 0
        assert result.modified_count == 0
        assert result.removed_count == 1

    def test_files_list_is_sorted_and_unique(self, mock_config, mock_git_ops):
        """Test that the combined files list is sorted and contains unique entries."""
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": ["z_file.py", "a_file.py"],
            "modified": ["m_file.py"],
            "removed": ["b_file.py"],
        }

        extractor = ChangedFilesLastCommitExtractor(config=mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Files should be sorted
        assert result.files == ["a_file.py", "b_file.py", "m_file.py", "z_file.py"]
        assert result.count == 4
