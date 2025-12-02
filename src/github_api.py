# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
GitHub API client wrapper using PyGithub.
Provides a clean interface to GitHub API operations with error handling.
"""

import logging
from typing import Any, Literal

from github import Auth, Github
from github.GithubException import GithubException
from github.Repository import Repository

from .constants import MAX_PR_FILES


class GitHubAPI:
    """Wrapper around PyGithub for common operations with context manager support."""

    def __init__(self, token: str | None = None, logger: logging.Logger | None = None):
        """
        Initialize GitHub API client.

        Args:
            token: GitHub authentication token (optional)
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
        self.client = None

        if token:
            try:
                auth = Auth.Token(token)
                self.client = Github(auth=auth)
                self.logger.debug("GitHub API client initialized with token")
            except Exception as e:
                self.logger.warning(f"Failed to initialize GitHub client with token: {e}")
                self.logger.warning("Falling back to unauthenticated access")
                self.client = Github()
        else:
            self.client = Github()
            self.logger.debug("GitHub API client initialized without authentication")

    def get_repository(self, repo_name: str) -> Repository:
        """
        Get repository object.

        Args:
            repo_name: Full repository name (owner/repo)

        Returns:
            Repository object

        Raises:
            GithubException: If repository cannot be accessed
        """
        if not self.client:
            raise GithubException(status=401, data={"message": "GitHub client not initialized"}, headers={})

        try:
            repo = self.client.get_repo(repo_name)
            self.logger.debug(f"Successfully fetched repository: {repo_name}")
            return repo
        except GithubException as e:
            self.logger.error(f"Failed to get repository {repo_name}: {e}")
            raise

    def get_pr_files(self, repo_name: str, pr_number: int, max_files: int = MAX_PR_FILES) -> list[str]:
        """
        Get list of changed files in a pull request.

        GitHub API returns up to 3000 files per PR. For extremely large PRs,
        some files may be omitted.

        Args:
            repo_name: Full repository name (owner/repo)
            pr_number: Pull request number
            max_files: Maximum number of files to return (default: MAX_PR_FILES)

        Returns:
            List of file paths changed in the PR

        Raises:
            GithubException: If PR cannot be accessed
        """
        try:
            repo = self.get_repository(repo_name)
            pr = repo.get_pull(pr_number)

            files = []
            for file in pr.get_files():
                files.append(file.filename)
                if len(files) >= max_files:
                    self.logger.warning(
                        f"PR #{pr_number} has more than {max_files} files, truncating list"
                    )
                    break

            self.logger.debug(f"Fetched {len(files)} files from PR #{pr_number}")
            return files
        except GithubException as e:
            self.logger.error(f"Failed to get PR #{pr_number} files: {e}")
            raise

    def get_pr_metadata(self, repo_name: str, pr_number: int) -> dict[str, Any]:
        """
        Get comprehensive PR metadata.

        Args:
            repo_name: Full repository name (owner/repo)
            pr_number: Pull request number

        Returns:
            Dictionary with PR metadata including:
                - number: PR number
                - source_branch: Head branch name
                - target_branch: Base branch name
                - commits_count: Number of commits
                - is_fork: Whether PR is from a fork
                - files_count: Number of files changed
                - additions: Lines added
                - deletions: Lines deleted

        Raises:
            GithubException: If PR cannot be accessed
        """
        try:
            repo = self.get_repository(repo_name)
            pr = repo.get_pull(pr_number)

            # Determine if PR is from a fork
            is_fork = False
            if pr.head.repo:
                is_fork = pr.head.repo.fork
            else:
                # If head.repo is None, the fork was deleted
                # We can infer it was a fork if the head label contains a colon
                is_fork = ":" in pr.head.label

            metadata = {
                "number": pr.number,
                "source_branch": pr.head.ref,
                "target_branch": pr.base.ref,
                "commits_count": pr.commits,
                "is_fork": is_fork,
                "files_count": pr.changed_files,
                "additions": pr.additions,
                "deletions": pr.deletions,
            }

            self.logger.debug(f"Fetched metadata for PR #{pr_number}")
            return metadata
        except GithubException as e:
            self.logger.error(f"Failed to get PR #{pr_number} metadata: {e}")
            raise

    def get_default_branch(self, repo_name: str) -> str:
        """
        Get repository default branch name.

        Args:
            repo_name: Full repository name (owner/repo)

        Returns:
            Default branch name (e.g., 'main' or 'master')

        Raises:
            GithubException: If repository cannot be accessed
        """
        try:
            repo = self.get_repository(repo_name)
            default_branch = str(repo.default_branch)
            self.logger.debug(f"Repository {repo_name} default branch: {default_branch}")
            return default_branch
        except GithubException as e:
            self.logger.error(f"Failed to get default branch for {repo_name}: {e}")
            raise

    def close(self):
        """Close the GitHub API client connection."""
        if self.client:
            self.client.close()
            self.logger.debug("GitHub API client closed")

    def __enter__(self):
        """Context manager entry - return self for use in with statement."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> Literal[False]:
        """Context manager exit - ensure client is closed."""
        self.close()
        return False  # Don't suppress exceptions
