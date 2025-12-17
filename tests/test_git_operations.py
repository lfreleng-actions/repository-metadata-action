# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for GitPython-based git operations module.
"""

from unittest.mock import Mock, patch

import pytest
from git import GitCommandError, InvalidGitRepositoryError, Repo
from git.exc import GitError

from src.exceptions import GitOperationError
from src.git_operations import GitOperations


class TestGitOperations:
    """Tests for GitOperations class."""

    @pytest.fixture
    def mock_repo(self):
        """Create a mock Repo object."""
        repo = Mock(spec=Repo)
        repo.git = Mock()
        return repo

    @pytest.fixture
    def git_ops(self, tmp_path):
        """Create GitOperations instance with temporary path."""
        return GitOperations(repo_path=tmp_path)

    @pytest.fixture
    def git_ops_with_repo(self, tmp_path, mock_repo):
        """Create GitOperations instance with mocked repo."""
        ops = GitOperations(repo_path=tmp_path)
        ops._repo = mock_repo
        ops._has_git = True
        return ops

    def test_initialization(self, tmp_path):
        """Test GitOperations initialization."""
        ops = GitOperations(repo_path=tmp_path)

        assert ops.repo_path == tmp_path
        assert ops._repo is None
        assert ops._has_git is None
        assert ops._is_shallow is None

    def test_initialization_with_logger(self, tmp_path):
        """Test initialization with custom logger."""
        import logging

        logger = logging.getLogger("test")

        ops = GitOperations(repo_path=tmp_path, logger=logger)
        assert ops.logger == logger

    def test_has_git_repo_true(self, tmp_path):
        """Test has_git_repo returns True when .git exists."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        ops = GitOperations(repo_path=tmp_path)
        assert ops.has_git_repo() is True
        # Should cache the result
        assert ops._has_git is True

    def test_has_git_repo_false(self, tmp_path):
        """Test has_git_repo returns False when .git doesn't exist."""
        ops = GitOperations(repo_path=tmp_path)
        assert ops.has_git_repo() is False
        assert ops._has_git is False

    def test_has_git_repo_cached(self, tmp_path):
        """Test has_git_repo caches result."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        ops = GitOperations(repo_path=tmp_path)

        # First call
        assert ops.has_git_repo() is True

        # Remove .git but should still return True due to caching
        git_dir.rmdir()
        assert ops.has_git_repo() is True

    @patch("src.git_operations.Repo")
    def test_repo_property_lazy_loads(self, mock_repo_class, tmp_path):
        """Test repo property lazy loads Repo instance."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        mock_repo_instance = Mock(spec=Repo)
        mock_repo_class.return_value = mock_repo_instance

        ops = GitOperations(repo_path=tmp_path)

        # First access should initialize
        repo = ops.repo
        assert repo == mock_repo_instance
        mock_repo_class.assert_called_once_with(tmp_path)

        # Second access should use cached value
        repo2 = ops.repo
        assert repo2 == mock_repo_instance
        assert mock_repo_class.call_count == 1

    @patch("src.git_operations.Repo")
    def test_repo_property_handles_invalid_repo(self, mock_repo_class, tmp_path):
        """Test repo property handles invalid repository."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        mock_repo_class.side_effect = InvalidGitRepositoryError()

        ops = GitOperations(repo_path=tmp_path)
        assert ops.repo is None

    def test_is_shallow_clone_true(self, tmp_path):
        """Test is_shallow_clone returns True for shallow clones."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        shallow_file = git_dir / "shallow"
        shallow_file.touch()

        ops = GitOperations(repo_path=tmp_path)
        assert ops.is_shallow_clone() is True
        assert ops._is_shallow is True

    def test_is_shallow_clone_false(self, tmp_path):
        """Test is_shallow_clone returns False for full clones."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        ops = GitOperations(repo_path=tmp_path)
        assert ops.is_shallow_clone() is False
        assert ops._is_shallow is False

    def test_is_shallow_clone_no_repo(self, tmp_path):
        """Test is_shallow_clone returns False when no repo exists."""
        ops = GitOperations(repo_path=tmp_path)
        assert ops.is_shallow_clone() is False

    def test_is_shallow_clone_cached(self, tmp_path):
        """Test is_shallow_clone caches result."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        shallow_file = git_dir / "shallow"
        shallow_file.touch()

        ops = GitOperations(repo_path=tmp_path)

        # First call
        assert ops.is_shallow_clone() is True

        # Remove shallow file but should still return True
        shallow_file.unlink()
        assert ops.is_shallow_clone() is True

    def test_get_commit_message(self, git_ops_with_repo, mock_repo):
        """Test get_commit_message returns subject line."""
        mock_commit = Mock()
        mock_commit.message = "Fix: bug in parser\n\nDetailed description here"
        mock_commit.summary = "Fix: bug in parser"
        mock_repo.commit.return_value = mock_commit

        result = git_ops_with_repo.get_commit_message("abc123")

        assert result == "Fix: bug in parser"
        mock_repo.commit.assert_called_once_with("abc123")

    def test_get_commit_message_single_line(self, git_ops_with_repo, mock_repo):
        """Test get_commit_message with single line message."""
        mock_commit = Mock()
        mock_commit.message = "Single line commit"
        mock_commit.summary = "Single line commit"
        mock_repo.commit.return_value = mock_commit

        result = git_ops_with_repo.get_commit_message()

        assert result == "Single line commit"

    def test_get_commit_message_no_repo(self, git_ops):
        """Test get_commit_message returns None without repo."""
        result = git_ops.get_commit_message()
        assert result is None

    def test_get_commit_message_git_error(self, git_ops_with_repo, mock_repo):
        """Test get_commit_message handles git errors."""
        mock_repo.commit.side_effect = GitCommandError("commit", "error")

        result = git_ops_with_repo.get_commit_message("invalid")
        assert result is None

    def test_get_commit_message_full(self, git_ops_with_repo, mock_repo):
        """Test get_commit_message_full returns full message."""
        mock_commit = Mock()
        mock_commit.message = "Fix: bug in parser\n\nDetailed description\nwith multiple lines"
        mock_repo.commit.return_value = mock_commit

        result = git_ops_with_repo.get_commit_message_full("abc123")

        assert result == "Fix: bug in parser\n\nDetailed description\nwith multiple lines"
        mock_repo.commit.assert_called_once_with("abc123")

    def test_get_commit_message_full_no_repo(self, git_ops):
        """Test get_commit_message_full returns None without repo."""
        result = git_ops.get_commit_message_full()
        assert result is None

    def test_get_commit_author(self, git_ops_with_repo, mock_repo):
        """Test get_commit_author returns author name."""
        mock_author = Mock()
        mock_author.name = "John Doe"
        mock_commit = Mock()
        mock_commit.author = mock_author
        mock_repo.commit.return_value = mock_commit

        result = git_ops_with_repo.get_commit_author("abc123")

        assert result == "John Doe"
        mock_repo.commit.assert_called_once_with("abc123")

    def test_get_commit_author_no_repo(self, git_ops):
        """Test get_commit_author returns None without repo."""
        result = git_ops.get_commit_author()
        assert result is None

    def test_get_commit_files_with_parent(self, git_ops_with_repo, mock_repo):
        """Test get_commit_files with parent commit."""
        # Setup mock commit with parent
        mock_parent = Mock()
        mock_commit = Mock()
        mock_commit.parents = [mock_parent]

        # Setup mock diffs
        mock_diff1 = Mock()
        mock_diff1.a_path = "file1.py"
        mock_diff1.b_path = "file1.py"

        mock_diff2 = Mock()
        mock_diff2.a_path = "file2.py"
        mock_diff2.b_path = "file2_renamed.py"

        mock_parent.diff.return_value = [mock_diff1, mock_diff2]
        mock_repo.commit.return_value = mock_commit

        result = git_ops_with_repo.get_commit_files("abc123")

        assert set(result) == {"file1.py", "file2.py", "file2_renamed.py"}
        mock_repo.commit.assert_called_once_with("abc123")

    def test_get_commit_files_initial_commit(self, git_ops_with_repo, mock_repo):
        """Test get_commit_files for initial commit (no parents)."""
        mock_commit = Mock()
        mock_commit.parents = []

        # Setup mock tree
        mock_item1 = Mock()
        mock_item1.path = "README.md"
        mock_item2 = Mock()
        mock_item2.path = "src/main.py"

        mock_tree = Mock()
        mock_tree.traverse.return_value = [mock_item1, mock_item2]
        mock_commit.tree = mock_tree

        mock_repo.commit.return_value = mock_commit

        result = git_ops_with_repo.get_commit_files("abc123")

        assert result == ["README.md", "src/main.py"]

    def test_get_commit_files_no_repo(self, git_ops):
        """Test get_commit_files returns empty list without repo."""
        result = git_ops.get_commit_files()
        assert result == []

    def test_diff_commits(self, git_ops_with_repo, mock_repo):
        """Test diff_commits between two commits."""
        mock_from = Mock()
        mock_to = Mock()

        mock_diff1 = Mock()
        mock_diff1.a_path = "file1.py"
        mock_diff1.b_path = "file1.py"

        mock_diff2 = Mock()
        mock_diff2.a_path = "old_name.py"
        mock_diff2.b_path = "new_name.py"

        mock_from.diff.return_value = [mock_diff1, mock_diff2]

        mock_repo.commit.side_effect = [mock_from, mock_to]

        result = git_ops_with_repo.diff_commits("abc123", "def456")

        assert set(result) == {"file1.py", "old_name.py", "new_name.py"}
        assert mock_repo.commit.call_count == 2

    def test_diff_commits_no_repo(self, git_ops):
        """Test diff_commits returns empty list without repo."""
        result = git_ops.diff_commits("abc123", "def456")
        assert result == []

    def test_diff_branches(self, git_ops_with_repo, mock_repo):
        """Test diff_branches with three-dot diff."""
        mock_base = Mock()
        mock_head = Mock()
        mock_merge_base = Mock()

        mock_diff1 = Mock()
        mock_diff1.a_path = "changed.py"
        mock_diff1.b_path = "changed.py"

        mock_merge_base.diff.return_value = [mock_diff1]

        mock_repo.commit.side_effect = [mock_base, mock_head]
        mock_repo.merge_base.return_value = [mock_merge_base]

        result = git_ops_with_repo.diff_branches("origin/main", "HEAD")

        assert result == ["changed.py"]
        mock_repo.merge_base.assert_called_once_with(mock_base, mock_head)

    def test_diff_branches_no_merge_base(self, git_ops_with_repo, mock_repo):
        """Test diff_branches falls back when no merge base."""
        mock_base = Mock()
        mock_head = Mock()

        mock_diff1 = Mock()
        mock_diff1.a_path = "file.py"
        mock_diff1.b_path = "file.py"

        mock_base.diff.return_value = [mock_diff1]

        # Need 4 commits: 2 for initial merge_base check, 2 for fallback diff
        mock_repo.commit.side_effect = [mock_base, mock_head, mock_base, mock_head]
        mock_repo.merge_base.return_value = []  # No merge base

        result = git_ops_with_repo.diff_branches("origin/main", "HEAD")

        assert result == ["file.py"]

    def test_diff_branches_no_repo(self, git_ops):
        """Test diff_branches returns empty list without repo."""
        result = git_ops.diff_branches("origin/main", "HEAD")
        assert result == []

    def test_fetch_branch_with_depth(self, git_ops_with_repo, mock_repo):
        """Test fetch_branch with depth."""
        mock_remote = Mock()
        mock_repo.remote.return_value = mock_remote

        git_ops_with_repo.fetch_branch("origin/feature", depth=5)

        mock_repo.remote.assert_called_once_with("origin")
        mock_remote.fetch.assert_called_once_with("feature:refs/remotes/origin/feature", depth=5)

    def test_fetch_branch_without_depth(self, git_ops_with_repo, mock_repo):
        """Test fetch_branch without depth."""
        mock_remote = Mock()
        mock_repo.remote.return_value = mock_remote

        git_ops_with_repo.fetch_branch("feature")

        mock_remote.fetch.assert_called_once_with("feature:refs/remotes/origin/feature")

    def test_fetch_branch_strips_origin_prefix(self, git_ops_with_repo, mock_repo):
        """Test fetch_branch strips origin/ prefix."""
        mock_remote = Mock()
        mock_repo.remote.return_value = mock_remote

        git_ops_with_repo.fetch_branch("origin/main", depth=1)

        mock_remote.fetch.assert_called_once_with("main:refs/remotes/origin/main", depth=1)

    def test_fetch_branch_no_repo(self, git_ops):
        """Test fetch_branch raises error without repo."""
        with pytest.raises(GitOperationError, match="No git repository available"):
            git_ops.fetch_branch("main")

    def test_fetch_branch_git_error(self, git_ops_with_repo, mock_repo):
        """Test fetch_branch handles git errors."""
        mock_remote = Mock()
        mock_remote.fetch.side_effect = GitError("Network error")
        mock_repo.remote.return_value = mock_remote

        with pytest.raises(GitOperationError, match="Failed to fetch"):
            git_ops_with_repo.fetch_branch("main")

    def test_deepen(self, git_ops_with_repo, mock_repo):
        """Test deepen repository."""
        git_ops_with_repo.deepen(15)

        mock_repo.git.fetch.assert_called_once_with("--deepen=15")

    def test_deepen_no_repo(self, git_ops):
        """Test deepen raises error without repo."""
        with pytest.raises(GitOperationError, match="No git repository available"):
            git_ops.deepen(15)

    def test_deepen_git_error(self, git_ops_with_repo, mock_repo):
        """Test deepen handles git errors."""
        mock_repo.git.fetch.side_effect = GitCommandError("fetch", "error")

        with pytest.raises(GitOperationError, match="Failed to deepen"):
            git_ops_with_repo.deepen(15)

    def test_get_files_from_show(self, git_ops_with_repo, mock_repo):
        """Test get_files_from_show returns file list."""
        mock_repo.git.show.return_value = "file1.py\nfile2.py\nfile3.py"

        result = git_ops_with_repo.get_files_from_show("abc123")

        assert result == ["file1.py", "file2.py", "file3.py"]
        mock_repo.git.show.assert_called_once_with("--pretty=", "--name-only", "abc123")

    def test_get_files_from_show_default_head(self, git_ops_with_repo, mock_repo):
        """Test get_files_from_show defaults to HEAD."""
        mock_repo.git.show.return_value = "file.py"

        result = git_ops_with_repo.get_files_from_show()

        assert result == ["file.py"]
        mock_repo.git.show.assert_called_once_with("--pretty=", "--name-only", "HEAD")

    def test_get_files_from_show_empty_output(self, git_ops_with_repo, mock_repo):
        """Test get_files_from_show with empty output."""
        mock_repo.git.show.return_value = ""

        result = git_ops_with_repo.get_files_from_show()

        assert result == []

    def test_get_files_from_show_no_repo(self, git_ops):
        """Test get_files_from_show returns empty list without repo."""
        result = git_ops.get_files_from_show()
        assert result == []

    def test_get_files_from_show_git_error(self, git_ops_with_repo, mock_repo):
        """Test get_files_from_show handles git errors."""
        mock_repo.git.show.side_effect = GitCommandError("show", "error")

        result = git_ops_with_repo.get_files_from_show()
        assert result == []
