# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Pull request metadata extractor.
Extracts PR-specific information from GitHub context and API.
"""

import re
from typing import TYPE_CHECKING

from ..models import PullRequestMetadata
from .base import BaseExtractor

import ijson

if TYPE_CHECKING:
    from ..config import Config
    from ..github_api import GitHubAPI


class PullRequestExtractor(BaseExtractor):
    """Extracts pull request metadata."""

    def __init__(
        self,
        config: "Config",
        github_api: "GitHubAPI | None" = None,
        **kwargs
    ):
        """
        Initialize pull request extractor.

        Args:
            config: Configuration object
            github_api: Optional GitHub API client
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(config, **kwargs)
        self.github_api = github_api

    def extract(self) -> PullRequestMetadata:
        """
        Extract pull request metadata from environment and API.

        Returns:
            PullRequestMetadata object with PR information
        """
        self.debug("Extracting pull request metadata")

        # Check if this is a pull request event
        if self.config.GITHUB_EVENT_NAME not in ["pull_request", "pull_request_target"]:
            self.debug("Not a pull request event, returning empty metadata")
            return PullRequestMetadata()

        # Extract PR number from GITHUB_REF or event payload
        pr_number = self._extract_pr_number()
        if not pr_number:
            self.warning("Could not extract PR number from GITHUB_REF or event payload")
            return PullRequestMetadata()

        self.info(f"Pull request: #{pr_number}")

        # Get source and target branches from environment
        source_branch = self.config.GITHUB_HEAD_REF
        target_branch = self.config.GITHUB_BASE_REF

        if source_branch:
            self.debug(f"PR source branch: {source_branch}")
        if target_branch:
            self.debug(f"PR target branch: {target_branch}")

        # Detect if PR is from a fork
        is_fork = self.config.PR_HEAD_REPO_FORK
        if is_fork:
            self.debug("PR is from a fork")

        # Try to get additional PR metadata from API
        commits_count = None
        if self.github_api and self.config.GITHUB_TOKEN:
            try:
                self.debug("Fetching PR metadata from GitHub API")
                pr_data = self.github_api.get_pr_metadata(
                    self.config.GITHUB_REPOSITORY,
                    pr_number
                )
                commits_count = pr_data.get("commits_count")
                if commits_count:
                    self.debug(f"PR has {commits_count} commits")
            except Exception as e:
                self.warning(f"Failed to fetch PR metadata from API: {e}")

        # Try to get PR data from event payload as fallback
        if commits_count is None and self.config.GITHUB_EVENT_PATH:
            commits_count = self._extract_commits_from_event()

        return PullRequestMetadata(
            number=pr_number,
            source_branch=source_branch,
            target_branch=target_branch,
            commits_count=commits_count,
            is_fork=is_fork
        )

    def _extract_pr_number(self) -> int | None:
        """
        Extract PR number from GITHUB_REF or event payload.

        Returns:
            PR number or None if not found
        """
        # Try GITHUB_REF first (faster, no I/O)
        if self.config.GITHUB_REF:
            match = re.match(r"refs/pull/(\d+)/", self.config.GITHUB_REF)
            if match:
                return int(match.group(1))

        # Fallback to event payload
        if self.config.GITHUB_EVENT_PATH and self.config.GITHUB_EVENT_PATH.exists():
            try:
                with open(self.config.GITHUB_EVENT_PATH, "rb") as f:
                    parser = ijson.items(f, "pull_request.number")
                    for pr_number in parser:
                        if pr_number:
                            self.debug(f"Got PR number from event payload: {pr_number}")
                            return int(pr_number)
            except Exception as e:
                self.debug(f"Failed to extract PR number from event: {e}")

        return None

    def _extract_commits_from_event(self) -> int | None:
        """
        Extract commit count from event payload.

        Returns:
            Number of commits or None if not available
        """
        try:
            if not self.config.GITHUB_EVENT_PATH or not self.config.GITHUB_EVENT_PATH.exists():
                return None

            with open(self.config.GITHUB_EVENT_PATH, "rb") as f:
                parser = ijson.items(f, "pull_request.commits")
                for commits in parser:
                    if commits is not None:
                        self.debug(f"Got commits count from event payload: {commits}")
                        return int(commits)

        except Exception as e:
            self.debug(f"Failed to extract commits from event payload: {e}")

        return None
