# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Commit metadata extractor.
Extracts commit information from git history.
"""

from typing import TYPE_CHECKING, Optional

from ..models import CommitMetadata
from .base import BaseExtractor

if TYPE_CHECKING:
    from ..config import Config
    from ..git_operations import GitOperations


class CommitExtractor(BaseExtractor):
    """Extracts commit metadata."""

    def __init__(
        self,
        config: "Config",
        git_ops: Optional["GitOperations"] = None,
        **kwargs
    ):
        """
        Initialize commit extractor.

        Args:
            config: Configuration object
            git_ops: Optional git operations handler
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(config, **kwargs)
        self.git_ops = git_ops

    def extract(self) -> CommitMetadata:
        """
        Extract commit metadata from environment and git.

        Returns:
            CommitMetadata object with commit information
        """
        self.debug("Extracting commit metadata")

        # Get SHA from environment (always available)
        commit_sha = self.config.GITHUB_SHA
        commit_sha_short = commit_sha[:7]

        self.info(f"Commit: {commit_sha_short}")

        # Try to get commit message and author from git if available
        commit_message = None
        commit_author = None

        if self.git_ops and self.git_ops.has_git_repo():
            try:
                self.debug("Fetching commit details from git")
                commit_message = self.git_ops.get_commit_message(commit_sha)
                commit_author = self.git_ops.get_commit_author(commit_sha)

                if commit_message:
                    self.debug(f"Commit message: {commit_message[:50]}...")
                if commit_author:
                    self.debug(f"Commit author: {commit_author}")
            except Exception as e:
                self.warning(f"Failed to fetch commit details from git: {e}")
        else:
            self.debug("Git repository not available, skipping commit details")

        return CommitMetadata(
            sha=commit_sha,
            sha_short=commit_sha_short,
            message=commit_message,
            author=commit_author
        )
