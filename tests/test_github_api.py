# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for GitHubAPI.
"""

from unittest.mock import Mock, patch

import pytest
from github import GithubException

from src.github_api import GitHubAPI


@pytest.fixture
def mock_github_client():
    """Create a mock GitHub client."""
    with patch("src.github_api.Github") as mock_github:
        client = Mock()
        mock_github.return_value = client
        yield mock_github, client


@pytest.fixture
def mock_auth():
    """Create a mock Auth.Token."""
    with patch("src.github_api.Auth") as mock_auth:
        token = Mock()
        mock_auth.Token.return_value = token
        yield mock_auth, token


class TestGitHubAPI:
    """Test suite for GitHubAPI."""

    def test_init_with_token(self, mock_auth, mock_github_client):
        """Test initialization with authentication token."""
        mock_github, mock_client = mock_github_client
        mock_auth_class, mock_token = mock_auth

        api = GitHubAPI(token="test-token")

        # Should create Auth.Token and pass to Github
        mock_auth_class.Token.assert_called_once_with("test-token")
        mock_github.assert_called_once_with(auth=mock_token)
        assert api.client == mock_client

    def test_init_without_token(self, mock_github_client):
        """Test initialization without token."""
        mock_github, mock_client = mock_github_client

        api = GitHubAPI(token=None)

        # Should create Github without auth
        mock_github.assert_called_once_with()
        assert api.client == mock_client

    def test_init_with_empty_token(self, mock_github_client):
        """Test initialization with empty token string."""
        mock_github, mock_client = mock_github_client

        api = GitHubAPI(token="")

        # Empty string is falsy, should init without auth
        mock_github.assert_called_once_with()
        assert api.client == mock_client

    def test_init_with_token_failure(self, mock_auth, mock_github_client):
        """Test initialization when token authentication fails."""
        mock_github, mock_client = mock_github_client
        mock_auth_class, _ = mock_auth

        # Make Auth.Token raise an exception
        mock_auth_class.Token.side_effect = Exception("Invalid token")

        api = GitHubAPI(token="bad-token")

        # Should fall back to unauthenticated
        assert api.client is not None

    def test_init_with_custom_logger(self, mock_github_client):
        """Test initialization with custom logger."""
        import logging

        custom_logger = logging.getLogger("test")

        api = GitHubAPI(logger=custom_logger)

        assert api.logger == custom_logger

    def test_get_repository_success(self, mock_github_client):
        """Test successful repository retrieval."""
        _, mock_client = mock_github_client
        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_repository("owner/repo")

        assert result == mock_repo
        mock_client.get_repo.assert_called_once_with("owner/repo")

    def test_get_repository_failure(self, mock_github_client):
        """Test repository retrieval failure."""
        _, mock_client = mock_github_client
        mock_client.get_repo.side_effect = GithubException(404, "Not found")

        api = GitHubAPI()

        with pytest.raises(GithubException):
            api.get_repository("owner/nonexistent")

    def test_get_repository_different_names(self, mock_github_client):
        """Test repository retrieval with different name formats."""
        _, mock_client = mock_github_client
        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()

        test_names = [
            "owner/repo",
            "organization/project-name",
            "user/repo_with_underscores",
            "org/repo.with.dots",
        ]

        for repo_name in test_names:
            result = api.get_repository(repo_name)
            assert result == mock_repo

    def test_get_pr_files_success(self, mock_github_client):
        """Test successful PR files retrieval."""
        _, mock_client = mock_github_client

        # Set up mock chain: client -> repo -> pr -> files
        mock_repo = Mock()
        mock_pr = Mock()
        mock_file1 = Mock()
        mock_file1.filename = "file1.py"
        mock_file2 = Mock()
        mock_file2.filename = "file2.js"
        mock_file3 = Mock()
        mock_file3.filename = "README.md"

        mock_pr.get_files.return_value = [mock_file1, mock_file2, mock_file3]
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_pr_files("owner/repo", 123)

        assert result == ["file1.py", "file2.js", "README.md"]
        mock_client.get_repo.assert_called_once_with("owner/repo")
        mock_repo.get_pull.assert_called_once_with(123)

    def test_get_pr_files_empty(self, mock_github_client):
        """Test PR with no changed files."""
        _, mock_client = mock_github_client

        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.get_files.return_value = []
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_pr_files("owner/repo", 456)

        assert result == []

    def test_get_pr_files_max_files_limit(self, mock_github_client):
        """Test PR files truncation at max_files limit."""
        _, mock_client = mock_github_client

        # Create many mock files
        mock_files = []
        for i in range(100):
            mock_file = Mock()
            mock_file.filename = f"file{i}.txt"
            mock_files.append(mock_file)

        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.get_files.return_value = mock_files
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_pr_files("owner/repo", 789, max_files=50)

        # Should only return 50 files
        assert len(result) == 50
        assert result[0] == "file0.txt"
        assert result[49] == "file49.txt"

    def test_get_pr_files_default_max_3000(self, mock_github_client):
        """Test default max_files is 3000."""
        _, mock_client = mock_github_client

        # Create 3500 mock files
        mock_files = []
        for i in range(3500):
            mock_file = Mock()
            mock_file.filename = f"file{i}.txt"
            mock_files.append(mock_file)

        mock_repo = Mock()
        mock_pr = Mock()
        mock_pr.get_files.return_value = mock_files
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_pr_files("owner/repo", 999)

        # Should truncate at default 3000
        assert len(result) == 3000

    def test_get_pr_files_failure(self, mock_github_client):
        """Test PR files retrieval failure."""
        _, mock_client = mock_github_client
        mock_client.get_repo.side_effect = GithubException(404, "Not found")

        api = GitHubAPI()

        with pytest.raises(GithubException):
            api.get_pr_files("owner/repo", 123)

    def test_get_pr_files_pr_not_found(self, mock_github_client):
        """Test when PR number doesn't exist."""
        _, mock_client = mock_github_client

        mock_repo = Mock()
        mock_repo.get_pull.side_effect = GithubException(404, "PR not found")
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()

        with pytest.raises(GithubException):
            api.get_pr_files("owner/repo", 99999)

    def test_get_pr_metadata_success(self, mock_github_client):
        """Test successful PR metadata retrieval."""
        _, mock_client = mock_github_client

        # Set up mock PR with all metadata
        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.head.ref = "feature/branch"
        mock_pr.base.ref = "main"
        mock_pr.commits = 5
        mock_pr.changed_files = 10
        mock_pr.additions = 100
        mock_pr.deletions = 50
        mock_pr.head.repo = Mock()
        mock_pr.head.repo.fork = False

        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_pr_metadata("owner/repo", 123)

        assert result["number"] == 123
        assert result["source_branch"] == "feature/branch"
        assert result["target_branch"] == "main"
        assert result["commits_count"] == 5
        assert result["is_fork"] is False
        assert result["files_count"] == 10
        assert result["additions"] == 100
        assert result["deletions"] == 50

    def test_get_pr_metadata_from_fork(self, mock_github_client):
        """Test PR metadata when PR is from a fork."""
        _, mock_client = mock_github_client

        mock_pr = Mock()
        mock_pr.number = 456
        mock_pr.head.ref = "fix/bug"
        mock_pr.base.ref = "develop"
        mock_pr.commits = 3
        mock_pr.changed_files = 5
        mock_pr.additions = 50
        mock_pr.deletions = 20
        mock_pr.head.repo = Mock()
        mock_pr.head.repo.fork = True

        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_pr_metadata("owner/repo", 456)

        assert result["is_fork"] is True

    def test_get_pr_metadata_deleted_fork(self, mock_github_client):
        """Test PR metadata when fork repo was deleted (head.repo is None)."""
        _, mock_client = mock_github_client

        mock_pr = Mock()
        mock_pr.number = 789
        mock_pr.head.ref = "patch"
        mock_pr.base.ref = "main"
        mock_pr.commits = 1
        mock_pr.changed_files = 1
        mock_pr.additions = 10
        mock_pr.deletions = 0
        mock_pr.head.repo = None  # Deleted fork
        mock_pr.head.label = "external-user:patch"  # Contains colon

        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_pr_metadata("owner/repo", 789)

        # Should infer is_fork from label containing colon
        assert result["is_fork"] is True

    def test_get_pr_metadata_deleted_fork_no_colon(self, mock_github_client):
        """Test PR metadata when fork deleted but label has no colon."""
        _, mock_client = mock_github_client

        mock_pr = Mock()
        mock_pr.number = 111
        mock_pr.head.ref = "branch"
        mock_pr.base.ref = "main"
        mock_pr.commits = 1
        mock_pr.changed_files = 1
        mock_pr.additions = 5
        mock_pr.deletions = 0
        mock_pr.head.repo = None
        mock_pr.head.label = "branch"  # No colon

        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_pr_metadata("owner/repo", 111)

        # No colon, so not a fork
        assert result["is_fork"] is False

    def test_get_pr_metadata_failure(self, mock_github_client):
        """Test PR metadata retrieval failure."""
        _, mock_client = mock_github_client
        mock_client.get_repo.side_effect = GithubException(403, "Forbidden")

        api = GitHubAPI()

        with pytest.raises(GithubException):
            api.get_pr_metadata("owner/private-repo", 123)

    def test_get_pr_metadata_zero_commits(self, mock_github_client):
        """Test PR with zero commits (edge case)."""
        _, mock_client = mock_github_client

        mock_pr = Mock()
        mock_pr.number = 222
        mock_pr.head.ref = "empty"
        mock_pr.base.ref = "main"
        mock_pr.commits = 0
        mock_pr.changed_files = 0
        mock_pr.additions = 0
        mock_pr.deletions = 0
        mock_pr.head.repo = Mock()
        mock_pr.head.repo.fork = False

        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_pr_metadata("owner/repo", 222)

        assert result["commits_count"] == 0
        assert result["files_count"] == 0
        assert result["additions"] == 0
        assert result["deletions"] == 0

    def test_get_default_branch_success(self, mock_github_client):
        """Test successful default branch retrieval."""
        _, mock_client = mock_github_client

        mock_repo = Mock()
        mock_repo.default_branch = "main"
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_default_branch("owner/repo")

        assert result == "main"
        mock_client.get_repo.assert_called_once_with("owner/repo")

    def test_get_default_branch_master(self, mock_github_client):
        """Test default branch retrieval for repos using 'master'."""
        _, mock_client = mock_github_client

        mock_repo = Mock()
        mock_repo.default_branch = "master"
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        result = api.get_default_branch("owner/repo")

        assert result == "master"

    def test_get_default_branch_custom(self, mock_github_client):
        """Test default branch retrieval for custom branch names."""
        _, mock_client = mock_github_client

        test_branches = ["develop", "trunk", "release", "production"]

        for branch_name in test_branches:
            mock_repo = Mock()
            mock_repo.default_branch = branch_name
            mock_client.get_repo.return_value = mock_repo

            api = GitHubAPI()
            result = api.get_default_branch("owner/repo")

            assert result == branch_name

    def test_get_default_branch_failure(self, mock_github_client):
        """Test default branch retrieval failure."""
        _, mock_client = mock_github_client
        mock_client.get_repo.side_effect = GithubException(404, "Not found")

        api = GitHubAPI()

        with pytest.raises(GithubException):
            api.get_default_branch("owner/nonexistent")

    def test_close(self, mock_github_client):
        """Test closing the GitHub API client."""
        _, mock_client = mock_github_client

        api = GitHubAPI()
        api.close()

        mock_client.close.assert_called_once()

    def test_close_no_client(self):
        """Test closing when client is None."""
        api = GitHubAPI()
        api.client = None

        # Should not crash
        api.close()

    def test_logging_debug_with_token(self, mock_auth, mock_github_client, caplog):
        """Test debug logging when initialized with token."""
        import logging

        caplog.set_level(logging.DEBUG)

        _ = GitHubAPI(token="test-token")

        assert "GitHub API client initialized with token" in caplog.text

    def test_logging_debug_without_token(self, mock_github_client, caplog):
        """Test debug logging when initialized without token."""
        import logging

        caplog.set_level(logging.DEBUG)

        _ = GitHubAPI()

        assert "GitHub API client initialized without authentication" in caplog.text

    def test_logging_warning_on_token_failure(self, mock_auth, mock_github_client, caplog):
        """Test warning logging when token auth fails."""
        import logging

        caplog.set_level(logging.WARNING)

        mock_auth_class, _ = mock_auth
        mock_auth_class.Token.side_effect = Exception("Bad token")

        _ = GitHubAPI(token="bad-token")

        assert "Failed to initialize GitHub client with token" in caplog.text
        assert "Falling back to unauthenticated access" in caplog.text

    def test_logging_repository_success(self, mock_github_client, caplog):
        """Test logging for successful repository fetch."""
        import logging

        caplog.set_level(logging.DEBUG)

        _, mock_client = mock_github_client
        mock_repo = Mock()
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        api.get_repository("owner/repo")

        assert "Successfully fetched repository: owner/repo" in caplog.text

    def test_logging_repository_failure(self, mock_github_client, caplog):
        """Test logging for failed repository fetch."""
        import logging

        caplog.set_level(logging.ERROR)

        _, mock_client = mock_github_client
        mock_client.get_repo.side_effect = GithubException(404, "Not found")

        api = GitHubAPI()

        try:
            api.get_repository("owner/repo")
        except GithubException:
            pass  # Expected exception - we're testing the logging output

        assert "Failed to get repository owner/repo" in caplog.text

    def test_logging_pr_files(self, mock_github_client, caplog):
        """Test logging for PR files fetch."""
        import logging

        caplog.set_level(logging.DEBUG)

        _, mock_client = mock_github_client
        mock_file = Mock()
        mock_file.filename = "test.py"
        mock_pr = Mock()
        mock_pr.get_files.return_value = [mock_file]
        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        api.get_pr_files("owner/repo", 123)

        assert "Fetched 1 files from PR #123" in caplog.text

    def test_logging_pr_files_truncated(self, mock_github_client, caplog):
        """Test logging warning when PR files are truncated."""
        import logging

        caplog.set_level(logging.WARNING)

        _, mock_client = mock_github_client
        mock_files = [Mock() for _ in range(100)]
        for i, f in enumerate(mock_files):
            f.filename = f"file{i}.txt"

        mock_pr = Mock()
        mock_pr.get_files.return_value = mock_files
        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        api.get_pr_files("owner/repo", 123, max_files=50)

        assert "PR #123 has more than 50 files, truncating list" in caplog.text

    def test_logging_pr_metadata(self, mock_github_client, caplog):
        """Test logging for PR metadata fetch."""
        import logging

        caplog.set_level(logging.DEBUG)

        _, mock_client = mock_github_client
        mock_pr = Mock()
        mock_pr.number = 123
        mock_pr.head.ref = "feature"
        mock_pr.base.ref = "main"
        mock_pr.commits = 5
        mock_pr.changed_files = 10
        mock_pr.additions = 100
        mock_pr.deletions = 50
        mock_pr.head.repo = Mock()
        mock_pr.head.repo.fork = False

        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        api.get_pr_metadata("owner/repo", 123)

        assert "Fetched metadata for PR #123" in caplog.text

    def test_logging_default_branch(self, mock_github_client, caplog):
        """Test logging for default branch fetch."""
        import logging

        caplog.set_level(logging.DEBUG)

        _, mock_client = mock_github_client
        mock_repo = Mock()
        mock_repo.default_branch = "main"
        mock_client.get_repo.return_value = mock_repo

        api = GitHubAPI()
        api.get_default_branch("owner/repo")

        assert "Repository owner/repo default branch: main" in caplog.text
