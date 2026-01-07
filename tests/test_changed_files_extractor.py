# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for ChangedFilesExtractor.
"""

import json
from unittest.mock import Mock, patch

import pytest

from src.extractors.changed_files import ChangedFilesExtractor
from src.models import ChangedFilesMetadata


@pytest.fixture
def mock_config():
    """Create a mock config object."""
    config = Mock()
    config.GITHUB_EVENT_NAME = "push"
    config.GITHUB_SHA = "abc123def456"
    config.GITHUB_REF = "refs/heads/main"
    config.GITHUB_REPOSITORY = "owner/repo"
    config.GITHUB_BASE_REF = "main"
    config.GITHUB_TOKEN = None
    config.GITHUB_EVENT_PATH = None
    config.CHANGE_DETECTION = "auto"
    config.GIT_FETCH_DEPTH = 50
    config.GITHUB_RUN_ID = "12345"
    config.GITHUB_WORKFLOW = "CI"
    config.DEBUG_MODE = False
    return config


@pytest.fixture
def mock_github_api():
    """Create a mock GitHub API client."""
    api = Mock()
    api.get_pr_files = Mock(return_value=["file1.py", "file2.js", "README.md"])
    return api


@pytest.fixture
def mock_git_ops():
    """Create a mock git operations handler."""
    git_ops = Mock()
    git_ops.has_git_repo = Mock(return_value=True)
    git_ops.diff_commits = Mock(return_value=["file1.py", "file2.js"])
    git_ops.get_commit_files = Mock(return_value=["file1.py"])
    git_ops.is_shallow_clone = Mock(return_value=False)
    git_ops.diff_branches = Mock(return_value=["file1.py", "file2.js"])
    git_ops.fetch_branch = Mock()
    git_ops.deepen = Mock()
    git_ops.get_files_from_show = Mock(return_value=["file1.py"])
    return git_ops


class TestChangedFilesExtractor:
    """Test suite for ChangedFilesExtractor."""

    def test_extract_push_event_basic(self, mock_config, mock_git_ops):
        """Test basic push event file extraction."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": ["file1.py"],
            "modified": ["file2.js"],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert isinstance(result, ChangedFilesMetadata)
        assert result.count == 2
        assert "file1.py" in result.files
        assert "file2.js" in result.files

    def test_extract_push_event_no_git(self, mock_config):
        """Test push event when git is not available."""
        mock_config.GITHUB_EVENT_NAME = "push"

        extractor = ChangedFilesExtractor(mock_config, git_ops=None)
        result = extractor.extract()

        assert result.count == 0
        assert result.files == []

    def test_extract_push_event_git_not_initialized(self, mock_config, mock_git_ops):
        """Test push event when git repo is not initialized."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_git_ops.has_git_repo.return_value = False

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 0
        assert result.files == []

    def test_extract_push_event_with_before_after(self, mock_config, mock_git_ops, tmp_path):
        """Test push event with before/after SHAs from event payload."""
        mock_config.GITHUB_EVENT_NAME = "push"

        # Create event payload with before/after
        event_path = tmp_path / "event.json"
        event_data = {
            "before": "a" * 40,
            "after": "b" * 40,
        }
        event_path.write_text(json.dumps(event_data))
        mock_config.GITHUB_EVENT_PATH = event_path

        mock_git_ops.diff_commits_categorized.return_value = {
            "added": ["file1.py", "file2.js"],
            "modified": ["file3.md"],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 3
        mock_git_ops.diff_commits_categorized.assert_called_once_with("a" * 40, "b" * 40)

    def test_extract_push_event_initial_push(self, mock_config, mock_git_ops, tmp_path):
        """Test push event with initial push (null before SHA)."""
        mock_config.GITHUB_EVENT_NAME = "push"

        # Create event payload with null before SHA
        event_path = tmp_path / "event.json"
        event_data = {
            "before": "0" * 40,  # Null SHA for initial push
            "after": "a" * 40,
        }
        event_path.write_text(json.dumps(event_data))
        mock_config.GITHUB_EVENT_PATH = event_path

        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": ["file1.py", "file2.js"],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 2
        mock_git_ops.get_commit_files_categorized.assert_called()

    def test_extract_push_event_before_is_null_string(self, mock_config, mock_git_ops, tmp_path):
        """Test push event with 'null' string as before SHA."""
        mock_config.GITHUB_EVENT_NAME = "push"

        event_path = tmp_path / "event.json"
        event_data = {
            "before": "null",
            "after": "abc123",
        }
        event_path.write_text(json.dumps(event_data))
        mock_config.GITHUB_EVENT_PATH = event_path

        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": ["file1.py"],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        _ = extractor.extract()

        # Should use diff-tree for null before
        mock_git_ops.get_commit_files_categorized.assert_called()

    def test_extract_push_event_no_event_path(self, mock_config, mock_git_ops):
        """Test push event without event payload file."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_config.GITHUB_EVENT_PATH = None

        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": ["file1.py"],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Should fallback to diff-tree
        assert result.count == 1
        mock_git_ops.get_commit_files_categorized.assert_called()

    def test_extract_push_event_exception(self, mock_config, mock_git_ops):
        """Test push event when git operations raise exception."""
        mock_config.GITHUB_EVENT_NAME = "push"
        mock_git_ops.get_commit_files.side_effect = Exception("Git error")

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Should handle exception gracefully
        assert result.count == 0
        assert result.files == []

    def test_extract_pr_event_api_strategy(self, mock_config, mock_github_api):
        """Test PR event using GitHub API strategy."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_REF = "refs/pull/123/merge"
        mock_config.GITHUB_TOKEN = "test-token"

        extractor = ChangedFilesExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.count == 3
        assert "file1.py" in result.files
        mock_github_api.get_pr_files.assert_called_once_with("owner/repo", 123)

    def test_extract_pr_event_git_strategy(self, mock_config, mock_git_ops):
        """Test PR event using git strategy."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_BASE_REF = "main"

        mock_git_ops.diff_branches_categorized.return_value = {
            "added": ["file1.py"],
            "modified": ["file2.js"],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 2
        mock_git_ops.diff_branches_categorized.assert_called_once()

    def test_extract_pr_event_pull_request_target(self, mock_config, mock_github_api):
        """Test pull_request_target event."""
        mock_config.GITHUB_EVENT_NAME = "pull_request_target"
        mock_config.GITHUB_REF = "refs/pull/456/merge"
        mock_config.GITHUB_TOKEN = "test-token"

        extractor = ChangedFilesExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.count == 3
        mock_github_api.get_pr_files.assert_called_once_with("owner/repo", 456)

    def test_extract_pr_explicit_api_strategy(self, mock_config, mock_github_api):
        """Test PR with explicit API strategy."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_REF = "refs/pull/789/merge"
        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.CHANGE_DETECTION = "github_api"

        extractor = ChangedFilesExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        assert result.count == 3
        mock_github_api.get_pr_files.assert_called_once()

    def test_extract_pr_explicit_git_strategy(self, mock_config, mock_git_ops):
        """Test PR with explicit git strategy."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.CHANGE_DETECTION = "git"
        mock_config.GITHUB_BASE_REF = "main"

        mock_git_ops.diff_branches_categorized.return_value = {
            "added": [],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        _ = extractor.extract()

        mock_git_ops.diff_branches_categorized.assert_called_once()

    def test_extract_pr_api_strategy_no_token(self, mock_config, mock_github_api):
        """Test PR API strategy when token is not available."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.CHANGE_DETECTION = "github_api"
        mock_config.GITHUB_TOKEN = None

        extractor = ChangedFilesExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        # No viable strategy
        assert result.count == 0

    def test_extract_pr_git_strategy_no_repo(self, mock_config, mock_git_ops):
        """Test PR git strategy when repo is not available."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.CHANGE_DETECTION = "git"
        mock_git_ops.has_git_repo.return_value = False

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # No viable strategy
        assert result.count == 0

    def test_extract_pr_auto_prefers_api(self, mock_config, mock_github_api, mock_git_ops):
        """Test PR auto mode prefers API when available."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_REF = "refs/pull/123/merge"
        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.CHANGE_DETECTION = "auto"

        extractor = ChangedFilesExtractor(
            mock_config, github_api=mock_github_api, git_ops=mock_git_ops
        )
        _ = extractor.extract()

        # Should use API, not git
        mock_github_api.get_pr_files.assert_called_once()
        mock_git_ops.diff_branches.assert_not_called()

    def test_extract_pr_auto_fallback_to_git(self, mock_config, mock_git_ops):
        """Test PR auto mode falls back to git when no API."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.CHANGE_DETECTION = "auto"
        mock_config.GITHUB_TOKEN = None
        mock_config.GITHUB_BASE_REF = "main"

        mock_git_ops.diff_branches_categorized.return_value = {
            "added": [],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        _ = extractor.extract()

        # Should use git
        mock_git_ops.diff_branches_categorized.assert_called_once()

    def test_extract_pr_api_invalid_ref(self, mock_config, mock_github_api):
        """Test PR API extraction with invalid ref."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_REF = "refs/heads/main"  # Not a PR ref
        mock_config.GITHUB_TOKEN = "test-token"

        extractor = ChangedFilesExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        # Cannot extract PR number
        assert result.count == 0

    def test_extract_pr_api_exception(self, mock_config, mock_github_api):
        """Test PR API extraction when API raises exception."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_REF = "refs/pull/123/merge"
        mock_config.GITHUB_TOKEN = "test-token"
        mock_github_api.get_pr_files.side_effect = Exception("API error")

        extractor = ChangedFilesExtractor(mock_config, github_api=mock_github_api)
        result = extractor.extract()

        # Should handle exception
        assert result.count == 0

    def test_extract_pr_git_shallow_clone(self, mock_config, mock_git_ops):
        """Test PR git extraction with shallow clone."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_BASE_REF = "main"
        mock_git_ops.is_shallow_clone.return_value = True
        mock_git_ops.diff_branches_categorized.return_value = {
            "added": ["file1.py"],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Should fetch base branch
        mock_git_ops.fetch_branch.assert_called_once_with("origin/main", depth=1)
        assert result.count == 1

    def test_extract_pr_git_shallow_fetch_failure(self, mock_config, mock_git_ops):
        """Test PR git extraction when shallow fetch fails."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_BASE_REF = "main"
        mock_git_ops.is_shallow_clone.return_value = True
        mock_git_ops.fetch_branch.side_effect = Exception("Fetch failed")
        mock_git_ops.diff_branches.return_value = ["file1.py"]

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        _ = extractor.extract()

        # Should try deepen
        mock_git_ops.deepen.assert_called_once_with(50)

    def test_extract_pr_git_deepen_failure(self, mock_config, mock_git_ops):
        """Test PR git extraction when deepen also fails."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_BASE_REF = "main"
        mock_git_ops.is_shallow_clone.return_value = True
        mock_git_ops.fetch_branch.side_effect = Exception("Fetch failed")
        mock_git_ops.deepen.side_effect = Exception("Deepen failed")
        mock_git_ops.diff_branches_categorized.return_value = {
            "added": [],
            "modified": [],
            "removed": [],
        }
        # Need to set up fallback strategies to also return empty
        mock_git_ops.diff_commits_categorized.return_value = {
            "added": [],
            "modified": [],
            "removed": [],
        }
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": [],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Should continue despite failures
        assert result.count == 0

    def test_extract_pr_git_no_base_ref(self, mock_config, mock_git_ops):
        """Test PR git extraction without base ref."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_BASE_REF = None
        mock_git_ops.diff_commits_categorized.return_value = {
            "added": ["file1.py"],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Should use fallback strategy
        assert result.count == 1

    def test_extract_pr_git_fallback_head_parent(self, mock_config, mock_git_ops):
        """Test PR git fallback to HEAD^1."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_BASE_REF = None
        mock_git_ops.diff_commits_categorized.return_value = {
            "added": ["file1.py", "file2.py"],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 2

    def test_extract_pr_git_fallback_diff_tree(self, mock_config, mock_git_ops):
        """Test PR git fallback to diff-tree."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_BASE_REF = None
        mock_git_ops.diff_commits_categorized.side_effect = Exception("Diff failed")
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": ["file1.py"],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 1
        mock_git_ops.get_commit_files_categorized.assert_called_once()

    def test_extract_pr_git_all_fallbacks_fail(self, mock_config, mock_git_ops):
        """Test PR git when all fallback strategies fail."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_config.GITHUB_BASE_REF = None
        mock_git_ops.diff_commits_categorized.side_effect = Exception("Failed")
        mock_git_ops.get_commit_files_categorized.side_effect = Exception("Failed")

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 0

    def test_extract_pr_git_exception(self, mock_config, mock_git_ops):
        """Test PR git extraction when exception occurs."""
        mock_config.GITHUB_EVENT_NAME = "pull_request"
        mock_git_ops.diff_branches.side_effect = Exception("Git error")

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Should handle exception
        assert result.count == 0

    def test_extract_other_event_types(self, mock_config):
        """Test extraction for other event types."""
        test_events = [
            "release",
            "workflow_dispatch",
            "schedule",
            "repository_dispatch",
        ]

        for event_name in test_events:
            mock_config.GITHUB_EVENT_NAME = event_name
            extractor = ChangedFilesExtractor(mock_config)
            result = extractor.extract()

            # Should return empty for unsupported events
            assert result.count == 0
            assert result.files == []

    def test_extract_push_shas_from_event_small_file(self, mock_config, tmp_path):
        """Test extracting SHAs from small event payload."""
        event_path = tmp_path / "event.json"
        event_data = {
            "before": "abc" * 13 + "a",  # 40 chars
            "after": "def" * 13 + "d",
        }
        event_path.write_text(json.dumps(event_data))
        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = ChangedFilesExtractor(mock_config)
        before, after = extractor._extract_push_shas_from_event()

        assert before == "abc" * 13 + "a"
        assert after == "def" * 13 + "d"

    def test_extract_push_shas_from_event_large_file(self, mock_config, tmp_path):
        """Test extracting SHAs from event payload (file size check)."""
        event_path = tmp_path / "event.json"

        # Create a file just under 1MB - should use regular JSON loading
        before_sha = "a" * 40  # Valid hex (all lowercase a's)
        after_sha = "b" * 40  # Valid hex (all lowercase b's)

        # Small file uses regular JSON.load() path
        event_data = {
            "before": before_sha,
            "after": after_sha,
            "commits": [{"sha": f"commit{i:040}", "message": "msg"} for i in range(100)],
        }
        event_path.write_text(json.dumps(event_data))

        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = ChangedFilesExtractor(mock_config)
        before, after = extractor._extract_push_shas_from_event()

        assert before == before_sha
        assert after == after_sha

    def test_extract_push_shas_no_file(self, mock_config, tmp_path):
        """Test extracting SHAs when file doesn't exist."""
        event_path = tmp_path / "nonexistent.json"
        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = ChangedFilesExtractor(mock_config)
        before, after = extractor._extract_push_shas_from_event()

        assert before is None
        assert after is None

    def test_extract_push_shas_invalid_json(self, mock_config, tmp_path):
        """Test extracting SHAs from invalid JSON."""
        event_path = tmp_path / "event.json"
        event_path.write_text("not valid json {")
        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = ChangedFilesExtractor(mock_config)
        before, after = extractor._extract_push_shas_from_event()

        # Should handle gracefully
        assert before is None
        assert after is None

    def test_extract_push_shas_missing_fields(self, mock_config, tmp_path):
        """Test extracting SHAs when fields are missing."""
        event_path = tmp_path / "event.json"
        event_data = {"action": "push"}
        event_path.write_text(json.dumps(event_data))
        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = ChangedFilesExtractor(mock_config)
        before, after = extractor._extract_push_shas_from_event()

        assert before is None
        assert after is None

    def test_changed_files_metadata_model_compliance(self, mock_config, mock_git_ops):
        """Test that extracted data complies with ChangedFilesMetadata model."""
        mock_git_ops.get_commit_files.return_value = ["file1.py", "file2.js"]

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        # Verify model fields exist
        assert hasattr(result, "count")
        assert hasattr(result, "files")

        # Verify types
        assert isinstance(result.count, int)
        assert isinstance(result.files, list)
        assert all(isinstance(f, str) for f in result.files)

    def test_extract_with_many_files(self, mock_config, mock_git_ops):
        """Test extraction with large number of files."""
        large_file_list = [f"file{i}.py" for i in range(1000)]
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": large_file_list[:500],
            "modified": large_file_list[500:],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 1000
        assert len(result.files) == 1000

    def test_extract_with_unicode_filenames(self, mock_config, mock_git_ops):
        """Test extraction with unicode filenames."""
        unicode_files = ["文件.py", "ファイル.js", "файл.md"]
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": unicode_files,
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 3
        assert all(f in result.files for f in unicode_files)

    def test_extract_with_special_char_filenames(self, mock_config, mock_git_ops):
        """Test extraction with special characters in filenames."""
        special_files = [
            "file with spaces.py",
            "file-with-dashes.js",
            "file_with_underscores.md",
            "file.multiple.dots.txt",
        ]
        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": special_files,
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        result = extractor.extract()

        assert result.count == 4
        assert all(f in result.files for f in special_files)

    def test_logging_output(self, mock_config, mock_git_ops, caplog):
        """Test that appropriate logging messages are generated."""
        import logging

        caplog.set_level(logging.INFO)

        mock_git_ops.get_commit_files_categorized.return_value = {
            "added": ["file1.py", "file2.js"],
            "modified": [],
            "removed": [],
        }

        extractor = ChangedFilesExtractor(mock_config, git_ops=mock_git_ops)
        _ = extractor.extract()

        assert "Detected 2 changed files" in caplog.text

    def test_logging_no_files(self, mock_config, caplog):
        """Test logging when no files are detected."""
        import logging

        caplog.set_level(logging.DEBUG)

        mock_config.DEBUG_MODE = True
        mock_config.GITHUB_EVENT_NAME = "release"

        extractor = ChangedFilesExtractor(mock_config)
        _ = extractor.extract()

        assert "No changed files detected" in caplog.text or "not applicable" in caplog.text

    def test_determine_pr_strategy(self, mock_config, mock_github_api, mock_git_ops):
        """Test _determine_pr_strategy method directly."""
        extractor = ChangedFilesExtractor(mock_config)

        # No tools available
        assert extractor._determine_pr_strategy() is None

        # Only API available
        mock_config.GITHUB_TOKEN = "token"
        extractor.github_api = mock_github_api
        assert extractor._determine_pr_strategy() == "api"

        # API and git available (should prefer API)
        extractor.git_ops = mock_git_ops
        assert extractor._determine_pr_strategy() == "api"

        # Only git available
        extractor.github_api = None
        mock_config.GITHUB_TOKEN = None
        assert extractor._determine_pr_strategy() == "git"

        # Explicit github_api setting
        mock_config.CHANGE_DETECTION = "github_api"
        mock_config.GITHUB_TOKEN = "token"
        extractor.github_api = mock_github_api
        assert extractor._determine_pr_strategy() == "api"

        # Explicit git setting
        mock_config.CHANGE_DETECTION = "git"
        assert extractor._determine_pr_strategy() == "git"

    def test_extract_push_shas_os_error(self, mock_config, tmp_path):
        """Test handling of OSError when reading event file."""
        event_path = tmp_path / "event.json"
        event_path.write_text('{"before": "abc", "after": "def"}')

        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = ChangedFilesExtractor(mock_config)

        # Mock open to raise OSError
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            before, after = extractor._extract_push_shas_from_event()

            # Should handle gracefully
            assert before is None
            assert after is None

    def test_extract_push_shas_io_error(self, mock_config, tmp_path):
        """Test handling of IOError when reading event file."""
        event_path = tmp_path / "event.json"
        event_path.write_text('{"before": "abc", "after": "def"}')

        mock_config.GITHUB_EVENT_PATH = event_path

        extractor = ChangedFilesExtractor(mock_config)

        # Mock open to raise IOError
        with patch("builtins.open", side_effect=OSError("Disk error")):
            before, after = extractor._extract_push_shas_from_event()

            # Should handle gracefully
            assert before is None
            assert after is None
