# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Repository metadata extractor.
"""

from typing import TYPE_CHECKING, Optional

from ..models import RepositoryMetadata
from .base import BaseExtractor

if TYPE_CHECKING:
    from ..config import Config
    from ..github_api import GitHubAPI


class RepositoryExtractor(BaseExtractor):
    """Extracts repository-related metadata."""

    def __init__(
        self,
        config: "Config",
        github_api: Optional["GitHubAPI"] = None,
        **kwargs
    ):
        """
        Initialize repository extractor.

        Args:
            config: Configuration object
            github_api: Optional GitHub API client
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(config, **kwargs)
        self.github_api = github_api

    def extract(self) -> RepositoryMetadata:
        """
        Extract repository metadata from environment and API.

        Returns:
            RepositoryMetadata object with repository information
        """
        self.debug("Extracting repository metadata")

        # Parse repository name from full name
        full_name = self.config.GITHUB_REPOSITORY
        owner = self.config.GITHUB_REPOSITORY_OWNER

        # Extract repo name by removing owner prefix
        if full_name.startswith(f"{owner}/"):
            name = full_name[len(owner) + 1:]
        else:
            # Fallback: take everything after first slash
            parts = full_name.split("/", 1)
            name = parts[1] if len(parts) > 1 else full_name

        # Determine visibility
        is_public = False
        is_private = False

        if self.config.REPO_VISIBILITY:
            # Use provided visibility from github.event.repository.visibility
            visibility = self.config.REPO_VISIBILITY.lower()
            is_public = visibility == "public"
            # Internal repositories are treated as private for access control
            is_private = visibility in ["private", "internal"]
            self.debug(f"Repository visibility from context: {visibility}")
        elif self.github_api and self.config.GITHUB_TOKEN:
            # Fetch from API if not provided
            try:
                self.debug("Fetching repository visibility from GitHub API")
                repo_data = self.github_api.get_repository(full_name)
                is_public = not repo_data.private
                is_private = repo_data.private
                self.debug(f"Repository visibility from API: public={is_public}, private={is_private}")
            except Exception as e:
                self.warning(f"Failed to fetch repository visibility from API: {e}")
        else:
            self.debug("Repository visibility not available (no REPO_VISIBILITY or API access)")

        self.info(f"Repository: {full_name} (public={is_public}, private={is_private})")

        return RepositoryMetadata(
            owner=owner,
            name=name,
            full_name=full_name,
            is_public=is_public,
            is_private=is_private
        )
