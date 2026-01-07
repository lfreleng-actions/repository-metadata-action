# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Changed files detection with multiple strategies.
Supports both GitHub API and git-based detection methods.
"""

import re
from typing import TYPE_CHECKING, Literal

from ..models import ChangedFilesMetadata
from .base import BaseExtractor

import ijson

if TYPE_CHECKING:
    from ..config import Config
    from ..git_operations import GitOperations
    from ..github_api import GitHubAPI


class ChangedFilesExtractor(BaseExtractor):
    """Detects changed files using GitHub API or git commands."""

    def __init__(
        self,
        config: "Config",
        github_api: "GitHubAPI | None" = None,
        git_ops: "GitOperations | None" = None,
        **kwargs
    ):
        """
        Initialize changed files extractor.

        Args:
            config: Configuration object
            github_api: Optional GitHub API client
            git_ops: Optional git operations handler
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(config, **kwargs)
        self.github_api = github_api
        self.git_ops = git_ops

    def extract(self) -> ChangedFilesMetadata:
        """
        Extract changed files based on event type and available tools.

        Returns:
            ChangedFilesMetadata object with list of changed files and categories
        """
        self.debug("Detecting changed files")

        files: list[str] = []
        added: list[str] = []
        modified: list[str] = []
        removed: list[str] = []
        event_name = self.config.GITHUB_EVENT_NAME

        if event_name == "push":
            files, categorized = self._extract_push_event()
            added = categorized.get("added", [])
            modified = categorized.get("modified", [])
            removed = categorized.get("removed", [])
        elif event_name in ["pull_request", "pull_request_target"]:
            files, categorized = self._extract_pull_request()
            added = categorized.get("added", [])
            modified = categorized.get("modified", [])
            removed = categorized.get("removed", [])
        else:
            self.debug(f"Changed files detection not applicable for event: {event_name}")

        if files:
            self.info(f"Detected {len(files)} changed files ({len(added)} added, {len(modified)} modified, {len(removed)} removed)")
        else:
            self.debug("No changed files detected")

        return ChangedFilesMetadata(
            count=len(files),
            files=files,
            added=added,
            modified=modified,
            removed=removed
        )

    def _extract_push_event(self) -> tuple[list[str], dict[str, list[str]]]:
        """
        Extract changed files for push events.

        For push events with multiple commits, we diff between before/after refs.
        For single commits or initial pushes, we use diff-tree.

        Returns:
            Tuple of (all files list, categorized dict with added/modified/removed)
        """
        if not self.git_ops or not self.git_ops.has_git_repo():
            self.warning("Git repository not available for push event changed files detection")
            return [], {"added": [], "modified": [], "removed": []}

        try:
            # Try to get before/after SHAs from event payload for multi-commit pushes
            before, after = self._extract_push_shas_from_event()

            if before and after:
                # Check if we have valid before SHA (not initial push)
                null_sha = "0" * 40
                if before != null_sha and before != "null":
                    self.debug(f"Using before/after SHAs from event: {before[:7]}..{after[:7]}")
                    categorized = self.git_ops.diff_commits_categorized(before, after)
                    all_files = categorized["added"] + categorized["modified"] + categorized["removed"]
                    return all_files, categorized

            # Fallback: Use diff-tree for single commit
            self.debug("Using diff-tree for single commit push")
            categorized = self.git_ops.get_commit_files_categorized(self.config.GITHUB_SHA)
            all_files = categorized["added"] + categorized["modified"] + categorized["removed"]
            return all_files, categorized

        except Exception as e:
            self.error("Failed to extract changed files for push event", e)
            return [], {"added": [], "modified": [], "removed": []}

    def _extract_push_shas_from_event(self) -> tuple[str | None, str | None]:
        """
        Extract before/after SHAs from event payload using streaming parser.

        Uses ijson for efficient streaming parsing.

        Returns:
            Tuple of (before_sha, after_sha) or (None, None) if not found
        """
        if not self.config.GITHUB_EVENT_PATH or not self.config.GITHUB_EVENT_PATH.exists():
            return None, None

        try:
            return self._extract_shas_with_ijson()
        except OSError as e:
            self.warning(f"Failed to read event payload: {e}")
            return None, None
        except Exception as e:
            self.debug(f"Error parsing event payload: {e}")
            return None, None

    def _extract_shas_with_ijson(self) -> tuple[str | None, str | None]:
        """
        Extract SHAs using ijson streaming parser.

        Returns:
            Tuple of (before_sha, after_sha) or (None, None) if not found
        """
        before_sha = None
        after_sha = None

        if not self.config.GITHUB_EVENT_PATH:
            return None, None

        with open(self.config.GITHUB_EVENT_PATH, "rb") as f:
            # Use ijson's kvitems to iterate over top-level key-value pairs
            # This is memory-efficient for all JSON files
            parser = ijson.kvitems(f, "")

            for key, value in parser:
                if key == "before" and isinstance(value, str):
                    before_sha = value
                    self.debug(f"Found before SHA: {before_sha[:7]}")
                elif key == "after" and isinstance(value, str):
                    after_sha = value
                    self.debug(f"Found after SHA: {after_sha[:7]}")

                # Stop once we have both
                if before_sha and after_sha:
                    break

        return before_sha, after_sha

    def _extract_pull_request(self) -> tuple[list[str], dict[str, list[str]]]:
        """
        Extract changed files for pull request events.

        Determines best strategy (API vs git) and delegates to appropriate method.

        Returns:
            Tuple of (all files list, categorized dict with added/modified/removed)
        """
        strategy = self._determine_pr_strategy()

        if strategy == "api":
            return self._extract_pr_api()
        if strategy == "git":
            return self._extract_pr_git()
        self.warning("No viable strategy for detecting PR changed files")
        return [], {"added": [], "modified": [], "removed": []}

    def _determine_pr_strategy(self) -> Literal["api", "git"] | None:
        """
        Determine best strategy for PR changed files detection.

        Priority:
        1. Respect explicit CHANGE_DETECTION setting
        2. Prefer API if token available (faster, no history needed)
        3. Fall back to git if available

        Returns:
            Strategy name ('api' or 'git') or None if no strategy available
        """
        if self.config.CHANGE_DETECTION == "github_api":
            if self.github_api and self.config.GITHUB_TOKEN:
                return "api"
            self.warning("github_api requested but not available")
            return None

        if self.config.CHANGE_DETECTION == "git":
            if self.git_ops and self.git_ops.has_git_repo():
                return "git"
            self.warning("git requested but repository not available")
            return None

        # Auto mode: prefer API, fallback to git
        if self.github_api and self.config.GITHUB_TOKEN:
            self.debug("Using GitHub API for PR files (auto mode)")
            return "api"

        if self.git_ops and self.git_ops.has_git_repo():
            self.debug("Using git for PR files (auto mode, no API token)")
            return "git"

        return None

    def _get_pr_number(self) -> int | None:
        """
        Get PR number from GITHUB_REF or event payload.

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

    def _extract_pr_api(self) -> tuple[list[str], dict[str, list[str]]]:
        """Extract PR changed files using GitHub API.

        Returns:
            Tuple of (all files list, categorized dict with added/modified/removed)
        """
        if not self.github_api:
            self.error("GitHub API client not available")
            return [], {"added": [], "modified": [], "removed": []}

        try:
            pr_number = self._get_pr_number()
            if not pr_number:
                self.error("Cannot extract PR number from GITHUB_REF or event payload")
                return [], {"added": [], "modified": [], "removed": []}

            self.debug(f"Fetching files for PR #{pr_number} via GitHub API")
            files = self.github_api.get_pr_files(
                self.config.GITHUB_REPOSITORY,
                pr_number
            )
            # API only returns file list without categorization
            # Would need additional API calls to get status per file
            # For now, return all as modified (conservative approach)
            return files, {"added": [], "modified": files, "removed": []}

        except Exception as e:
            self.error("Failed to fetch PR files via API", e)
            return [], {"added": [], "modified": [], "removed": []}

    def _extract_pr_git(self) -> tuple[list[str], dict[str, list[str]]]:
        """
        Extract PR changed files using git commands.

        This method:
        - Handles shallow clones by fetching base branch if needed
        - Uses three-dot diff (base...head) to show PR changes
        - Falls back through multiple strategies if needed

        Returns:
            Tuple of (all files list, categorized dict with added/modified/removed)
        """
        if not self.git_ops:
            self.error("Git operations handler not available")
            return [], {"added": [], "modified": [], "removed": []}

        try:
            base_ref = self.config.GITHUB_BASE_REF
            if not base_ref:
                self.warning("GITHUB_BASE_REF not available for PR")
                return self._extract_pr_git_fallback()

            # Ensure we have the base branch for shallow clones
            if self.git_ops.is_shallow_clone():
                self.debug("Shallow clone detected, fetching base branch")
                try:
                    # Try minimal fetch first
                    self.git_ops.fetch_branch(f"origin/{base_ref}", depth=1)
                except Exception as e:
                    self.debug(f"Minimal fetch failed, trying deepen: {e}")
                    try:
                        self.git_ops.deepen(self.config.GIT_FETCH_DEPTH)
                    except Exception as e2:
                        self.warning(f"Failed to fetch sufficient history: {e2}")

            # Try to diff against base branch
            self.debug(f"Diffing against base branch: origin/{base_ref}")
            categorized = self.git_ops.diff_branches_categorized(f"origin/{base_ref}", "HEAD")
            all_files = categorized["added"] + categorized["modified"] + categorized["removed"]

            if all_files:
                return all_files, categorized

            # If no files found, try fallback strategies
            self.debug("No files from base diff, trying fallback")
            return self._extract_pr_git_fallback()

        except Exception as e:
            self.error("Failed to extract PR files via git", e)
            return [], {"added": [], "modified": [], "removed": []}

    def _extract_pr_git_fallback(self) -> tuple[list[str], dict[str, list[str]]]:
        """
        Fallback strategies for PR file detection when base branch unavailable.

        Tries multiple strategies in order:
        1. Diff against HEAD^1 (first parent)
        2. Diff-tree for HEAD

        Returns:
            Tuple of (all files list, categorized dict with added/modified/removed)
        """
        if not self.git_ops:
            self.error("Git operations handler not available for fallback")
            return [], {"added": [], "modified": [], "removed": []}

        strategies = [
            ("HEAD^1", lambda: self.git_ops.diff_commits_categorized("HEAD^1", "HEAD")),  # type: ignore[union-attr]
            ("diff-tree", lambda: self.git_ops.get_commit_files_categorized("HEAD")),  # type: ignore[union-attr]
        ]

        for strategy_name, strategy_func in strategies:
            try:
                self.debug(f"Trying fallback strategy: {strategy_name}")
                categorized = strategy_func()
                all_files = categorized["added"] + categorized["modified"] + categorized["removed"]
                if all_files:
                    self.debug(f"Got {len(all_files)} files from {strategy_name}")
                    return all_files, categorized
            except Exception as e:
                self.debug(f"Strategy {strategy_name} failed: {e}")

        self.warning("All PR git fallback strategies failed")
        return [], {"added": [], "modified": [], "removed": []}

    def _get_files_from_show(self) -> list[str]:
        """
        Get changed files using 'git show' command.

        Useful for merge commits where diff-tree might not work well.

        Returns:
            List of changed file paths
        """
        if not self.git_ops:
            return []
        return self.git_ops.get_files_from_show("HEAD")
