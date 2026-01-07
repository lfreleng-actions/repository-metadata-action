# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Ref (branch/tag) metadata extractor.
Extracts branch and tag information from GitHub context.
"""

from typing import TYPE_CHECKING, Optional

from ..models import RefMetadata
from .base import BaseExtractor

if TYPE_CHECKING:
    from ..config import Config
    from ..github_api import GitHubAPI


class RefExtractor(BaseExtractor):
    """Extracts branch and tag metadata."""

    def __init__(
        self,
        config: "Config",
        github_api: Optional["GitHubAPI"] = None,
        **kwargs
    ):
        """
        Initialize ref extractor.

        Args:
            config: Configuration object
            github_api: Optional GitHub API client for default branch detection
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(config, **kwargs)
        self.github_api = github_api

    def extract(self) -> RefMetadata:
        """
        Extract branch/tag metadata from environment.

        Returns:
            RefMetadata object with branch/tag information
        """
        self.debug("Extracting ref metadata")

        branch_name = None
        tag_name = None
        is_default_branch = False
        is_main_branch = False

        # Extract branch or tag name based on ref type
        ref_type = self.config.GITHUB_REF_TYPE
        ref_name = self.config.GITHUB_REF_NAME

        if ref_type == "branch" and ref_name:
            branch_name = ref_name
            self.info(f"Branch: {branch_name}")

            # Check if this is main or master
            if branch_name in ["main", "master"]:
                is_main_branch = True
                self.debug(f"Detected main branch: {branch_name}")

            # Check if this is the default branch
            is_default_branch = self._check_default_branch(branch_name)

        elif ref_type == "tag" and ref_name:
            tag_name = ref_name
            self.info(f"Tag: {tag_name}")

        # For pull requests, we might have branch info from HEAD_REF
        if not branch_name and self.config.GITHUB_HEAD_REF:
            # This is the source branch for a PR
            self.debug(f"Using HEAD_REF for branch context: {self.config.GITHUB_HEAD_REF}")

        return RefMetadata(
            branch_name=branch_name,
            tag_name=tag_name,
            is_default_branch=is_default_branch,
            is_main_branch=is_main_branch
        )

    def _check_default_branch(self, branch_name: str) -> bool:
        """
        Check if the given branch is the repository's default branch.

        Args:
            branch_name: Branch name to check

        Returns:
            True if branch is the default branch
        """
        # First check if DEFAULT_BRANCH was provided
        if self.config.DEFAULT_BRANCH:
            is_default = branch_name == self.config.DEFAULT_BRANCH
            if is_default:
                self.debug(f"Branch matches provided default branch: {self.config.DEFAULT_BRANCH}")
            return is_default

        # Try to auto-detect using GitHub API
        if self.github_api and self.config.GITHUB_TOKEN:
            try:
                self.debug("Auto-detecting default branch via GitHub API")
                default_branch = self.github_api.get_default_branch(
                    self.config.GITHUB_REPOSITORY
                )
                is_default = branch_name == default_branch
                if is_default:
                    self.info(f"Branch is the default branch: {default_branch}")
                return is_default
            except Exception as e:
                self.debug(f"Failed to auto-detect default branch: {e}")

        self.debug("Cannot determine if branch is default (no DEFAULT_BRANCH input or API access)")
        return False
