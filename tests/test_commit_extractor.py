# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for CommitExtractor.
"""

from unittest.mock import Mock

import pytest

from src.extractors.commit import CommitExtractor
from src.models import CommitMetadata


@pytest.fixture
def mock_config():
    """Create a mock config object."""
    config = Mock()
    config.GITHUB_SHA = "abc123def456789012345678901234567890abcd"
    config.GITHUB_RUN_ID = "12345"
    config.GITHUB_WORKFLOW = "CI"
    config.DEBUG_MODE = False
    return config


@pytest.fixture
def mock_git_ops():
    """Create a mock git operations handler."""
    git_ops = Mock()
    git_ops.has_git_repo = Mock(return_value=True)
    git_ops.get_commit_message = Mock(return_value="feat: Add new feature")
    git_ops.get_commit_author = Mock(return_value="John Doe <john@example.com>")
    return git_ops


class TestCommitExtractor:
    """Test suite for CommitExtractor."""

    def test_extract_basic_commit_info(self, mock_config):
        """Test extraction of basic commit information without git."""
        extractor = CommitExtractor(mock_config)
        result = extractor.extract()

        assert isinstance(result, CommitMetadata)
        assert result.sha == "abc123def456789012345678901234567890abcd"
        assert result.sha_short == "abc123d"
        assert result.message is None
        assert result.author is None

    def test_extract_with_git_operations(self, mock_config, mock_git_ops):
        """Test extraction with git operations available."""
        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.sha == "abc123def456789012345678901234567890abcd"
        assert result.sha_short == "abc123d"
        assert result.message == "feat: Add new feature"
        assert result.author == "John Doe <john@example.com>"

        mock_git_ops.has_git_repo.assert_called_once()
        mock_git_ops.get_commit_message.assert_called_once_with(
            "abc123def456789012345678901234567890abcd"
        )
        mock_git_ops.get_commit_author.assert_called_once_with(
            "abc123def456789012345678901234567890abcd"
        )

    def test_extract_short_sha_format(self, mock_config):
        """Test that short SHA is first 7 characters."""
        mock_config.GITHUB_SHA = "1234567890abcdef"

        extractor = CommitExtractor(mock_config)
        result = extractor.extract()

        assert result.sha_short == "1234567"
        assert len(result.sha_short) == 7

    def test_extract_with_short_sha_input(self, mock_config):
        """Test extraction when SHA is already short (less than 7 chars)."""
        mock_config.GITHUB_SHA = "abc1234"  # 7 chars

        extractor = CommitExtractor(mock_config)
        result = extractor.extract()

        assert result.sha == "abc1234"
        assert result.sha_short == "abc1234"

    def test_extract_with_exact_7_char_sha(self, mock_config):
        """Test extraction with exactly 7 character SHA."""
        mock_config.GITHUB_SHA = "1234567"

        extractor = CommitExtractor(mock_config)
        result = extractor.extract()

        assert result.sha == "1234567"
        assert result.sha_short == "1234567"

    def test_extract_git_repo_not_available(self, mock_config, mock_git_ops):
        """Test extraction when git repository is not available."""
        mock_git_ops.has_git_repo.return_value = False

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.sha == "abc123def456789012345678901234567890abcd"
        assert result.sha_short == "abc123d"
        assert result.message is None
        assert result.author is None

        # Should check for repo but not call get methods
        mock_git_ops.has_git_repo.assert_called_once()
        mock_git_ops.get_commit_message.assert_not_called()
        mock_git_ops.get_commit_author.assert_not_called()

    def test_extract_git_message_failure(self, mock_config, mock_git_ops):
        """Test extraction when getting commit message fails."""
        mock_git_ops.get_commit_message.side_effect = Exception("Git error")

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Should not crash, falls back to None
        assert result.sha == "abc123def456789012345678901234567890abcd"
        assert result.message is None
        assert result.author is None

    def test_extract_git_author_failure(self, mock_config, mock_git_ops):
        """Test extraction when getting commit author fails."""
        mock_git_ops.get_commit_message.return_value = "Test message"
        mock_git_ops.get_commit_author.side_effect = Exception("Git error")

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Should get message but not author
        assert result.message == "Test message"
        assert result.author is None

    def test_extract_with_empty_commit_message(self, mock_config, mock_git_ops):
        """Test extraction with empty commit message."""
        mock_git_ops.get_commit_message.return_value = ""

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.message == ""
        assert result.author == "John Doe <john@example.com>"

    def test_extract_with_empty_commit_author(self, mock_config, mock_git_ops):
        """Test extraction with empty commit author."""
        mock_git_ops.get_commit_author.return_value = ""

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.message == "feat: Add new feature"
        assert result.author == ""

    def test_extract_with_none_commit_message(self, mock_config, mock_git_ops):
        """Test extraction when git returns None for commit message."""
        mock_git_ops.get_commit_message.return_value = None

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.message is None
        assert result.author == "John Doe <john@example.com>"

    def test_extract_with_none_commit_author(self, mock_config, mock_git_ops):
        """Test extraction when git returns None for commit author."""
        mock_git_ops.get_commit_author.return_value = None

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.message == "feat: Add new feature"
        assert result.author is None

    def test_extract_with_multiline_commit_message(self, mock_config, mock_git_ops):
        """Test extraction with multiline commit message."""
        message = "feat: Add new feature\n\nThis is a detailed description\nof the commit."
        mock_git_ops.get_commit_message.return_value = message

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.message == message

    def test_extract_with_long_commit_message(self, mock_config, mock_git_ops):
        """Test extraction with very long commit message."""
        message = "a" * 1000
        mock_git_ops.get_commit_message.return_value = message

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.message == message
        assert len(result.message) == 1000

    def test_extract_with_unicode_commit_message(self, mock_config, mock_git_ops):
        """Test extraction with unicode characters in commit message."""
        message = "feat: Add 新功能 with émojis 🎉"
        mock_git_ops.get_commit_message.return_value = message

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.message == message

    def test_extract_with_unicode_commit_author(self, mock_config, mock_git_ops):
        """Test extraction with unicode characters in author name."""
        author = "山田太郎 <yamada@example.com>"
        mock_git_ops.get_commit_author.return_value = author

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.author == author

    def test_extract_with_conventional_commit_message(self, mock_config, mock_git_ops):
        """Test extraction with conventional commit format."""
        test_messages = [
            "feat: add new feature",
            "fix: resolve bug #123",
            "docs: update README",
            "chore: update dependencies",
            "test: add unit tests",
            "refactor: improve code structure",
        ]

        for message in test_messages:
            mock_git_ops.get_commit_message.return_value = message
            extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
            result = extractor.extract()
            assert result.message == message

    def test_extract_with_merge_commit_message(self, mock_config, mock_git_ops):
        """Test extraction with merge commit message."""
        message = "Merge pull request #123 from user/branch\n\nFeature description"
        mock_git_ops.get_commit_message.return_value = message

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.message == message

    def test_extract_with_different_author_formats(self, mock_config, mock_git_ops):
        """Test extraction with different author format variations."""
        test_authors = [
            "John Doe <john@example.com>",
            "jane.doe@example.com",
            "Bot User <noreply@github.com>",
            "dependabot[bot] <49699333+dependabot[bot]@users.noreply.github.com>",
        ]

        for author in test_authors:
            mock_git_ops.get_commit_author.return_value = author
            extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
            result = extractor.extract()
            assert result.author == author

    def test_extract_with_full_40_char_sha(self, mock_config):
        """Test extraction with full 40-character SHA."""
        sha = "a" * 40
        mock_config.GITHUB_SHA = sha

        extractor = CommitExtractor(mock_config)
        result = extractor.extract()

        assert result.sha == sha
        assert result.sha_short == "aaaaaaa"
        assert len(result.sha) == 40
        assert len(result.sha_short) == 7

    def test_extract_sha_consistency(self, mock_config):
        """Test that SHA values are consistent."""
        extractor = CommitExtractor(mock_config)
        result = extractor.extract()

        # Short SHA should be prefix of full SHA
        assert result.sha.startswith(result.sha_short)

    def test_logging_output(self, mock_config, caplog):
        """Test that appropriate logging messages are generated."""
        import logging

        caplog.set_level(logging.INFO)

        mock_config.DEBUG_MODE = True

        extractor = CommitExtractor(mock_config)
        _ = extractor.extract()

        assert "Commit: abc123d" in caplog.text

    def test_logging_git_operations(self, mock_config, mock_git_ops, caplog):
        """Test logging when using git operations."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.DEBUG_MODE = True

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        _ = extractor.extract()

        assert "Fetching commit details from git" in caplog.text
        assert "Commit message: feat: Add new feature" in caplog.text
        assert "Commit author: John Doe <john@example.com>" in caplog.text

    def test_logging_git_not_available(self, mock_config, mock_git_ops, caplog):
        """Test logging when git is not available."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.DEBUG_MODE = True
        mock_git_ops.has_git_repo.return_value = False

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        _ = extractor.extract()

        assert "Git repository not available, skipping commit details" in caplog.text

    def test_logging_git_failure(self, mock_config, mock_git_ops, caplog):
        """Test logging when git operations fail."""
        import logging

        caplog.set_level(logging.WARNING)

        mock_config.DEBUG_MODE = True
        mock_git_ops.get_commit_message.side_effect = Exception("Git error")

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        _ = extractor.extract()

        assert "Failed to fetch commit details from git" in caplog.text

    def test_logging_long_commit_message_truncated(self, mock_config, mock_git_ops, caplog):
        """Test that long commit messages are truncated in logs."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.DEBUG_MODE = True
        long_message = "a" * 100
        mock_git_ops.get_commit_message.return_value = long_message

        extractor = CommitExtractor(mock_config, git_ops=mock_git_ops)
        _ = extractor.extract()

        # Log should contain truncated message (first 50 chars + ...)
        assert "Commit message: " + "a" * 50 + "..." in caplog.text

    def test_commit_metadata_model_compliance(self, mock_config):
        """Test that extracted data complies with CommitMetadata model."""
        extractor = CommitExtractor(mock_config)
        result = extractor.extract()

        # Verify model fields exist
        assert hasattr(result, "sha")
        assert hasattr(result, "sha_short")
        assert hasattr(result, "message")
        assert hasattr(result, "author")

        # Verify types
        assert isinstance(result.sha, str)
        assert isinstance(result.sha_short, str)
        assert isinstance(result.message, str) or result.message is None
        assert isinstance(result.author, str) or result.author is None

    def test_extract_no_git_ops_provided(self, mock_config):
        """Test extraction when no git operations handler is provided."""
        extractor = CommitExtractor(mock_config, git_ops=None)
        result = extractor.extract()

        assert result.sha == "abc123def456789012345678901234567890abcd"
        assert result.sha_short == "abc123d"
        assert result.message is None
        assert result.author is None

    def test_extract_deterministic_sha_short(self, mock_config):
        """Test that sha_short generation is deterministic."""
        extractor1 = CommitExtractor(mock_config)
        result1 = extractor1.extract()

        extractor2 = CommitExtractor(mock_config)
        result2 = extractor2.extract()

        assert result1.sha_short == result2.sha_short
        assert result1.sha == result2.sha
