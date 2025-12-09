# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Changed files detection with multiple strategies.
Supports both GitHub API and git-based detection methods.
"""

import json
import re
from typing import TYPE_CHECKING, Literal

from ..constants import (
    MAX_EVENT_LINES_TO_SCAN,
    SMALL_FILE_MAX_BYTES,
)
from ..models import ChangedFilesMetadata
from .base import BaseExtractor

try:
    import ijson
    HAS_IJSON = True
except ImportError:
    HAS_IJSON = False

if TYPE_CHECKING:
    from ..config import Config
    from ..git_operations import GitOperations
    from ..github_api import GitHubAPI


class ChangedFilesExtractor(BaseExtractor):
    """Detects changed files using GitHub API or git commands."""

    # Precompiled regex patterns for event payload parsing (fallback method)
    _BEFORE_SHA_PATTERN = re.compile(r'"before":\s*"([a-f0-9]{40})"')
    _AFTER_SHA_PATTERN = re.compile(r'"after":\s*"([a-f0-9]{40})"')

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
            ChangedFilesMetadata object with list of changed files
        """
        self.debug("Detecting changed files")

        files = []
        event_name = self.config.GITHUB_EVENT_NAME

        if event_name == "push":
            files = self._extract_push_event()
        elif event_name in ["pull_request", "pull_request_target"]:
            files = self._extract_pull_request()
        else:
            self.debug(f"Changed files detection not applicable for event: {event_name}")

        if files:
            self.info(f"Detected {len(files)} changed files")
        else:
            self.debug("No changed files detected")

        return ChangedFilesMetadata(
            count=len(files),
            files=files
        )

    def _extract_push_event(self) -> list[str]:
        """
        Extract changed files for push events.

        For push events with multiple commits, we diff between before/after refs.
        For single commits or initial pushes, we use diff-tree.

        Returns:
            List of changed file paths
        """
        if not self.git_ops or not self.git_ops.has_git_repo():
            self.warning("Git repository not available for push event changed files detection")
            return []

        try:
            # Try to get before/after SHAs from event payload for multi-commit pushes
            before, after = self._extract_push_shas_from_event()

            if before and after:
                # Check if we have valid before SHA (not initial push)
                null_sha = "0" * 40
                if before != null_sha and before != "null":
                    self.debug(f"Using before/after SHAs from event: {before[:7]}..{after[:7]}")
                    return self.git_ops.diff_commits(before, after)

            # Fallback: Use diff-tree for single commit
            self.debug("Using diff-tree for single commit push")
            return self.git_ops.get_commit_files(self.config.GITHUB_SHA)

        except Exception as e:
            self.error("Failed to extract changed files for push event", e)
            return []

    def _extract_push_shas_from_event(self) -> tuple[str | None, str | None]:
        """
        Extract before/after SHAs from event payload using streaming parser.

        Uses ijson for efficient streaming parsing on large files, with fallback
        to standard JSON loading for small files.

        Returns:
            Tuple of (before_sha, after_sha) or (None, None) if not found
        """
        if not self.config.GITHUB_EVENT_PATH or not self.config.GITHUB_EVENT_PATH.exists():
            return None, None

        try:
            # Check file size first
            file_size = self.config.GITHUB_EVENT_PATH.stat().st_size

            # For small files, use regular JSON loading for better performance
            if file_size < SMALL_FILE_MAX_BYTES:
                with open(self.config.GITHUB_EVENT_PATH) as f:
                    event = json.load(f)
                return event.get("before"), event.get("after")

            # For large files, use streaming approach
            self.debug(f"Large event payload ({file_size} bytes), using streaming parser")

            # Use ijson if available (more efficient), otherwise fallback to regex
            if HAS_IJSON:
                return self._extract_shas_with_ijson()
            self.debug("ijson not available, using regex fallback")
            return self._extract_shas_with_regex()

        except OSError as e:
            self.warning(f"Failed to read event payload: {e}")
            return None, None
        except Exception as e:
            self.debug(f"Error parsing event payload: {e}")
            return None, None

    def _extract_shas_with_ijson(self) -> tuple[str | None, str | None]:
        """
        Extract SHAs using ijson streaming parser (most efficient).

        Returns:
            Tuple of (before_sha, after_sha) or (None, None) if not found
        """
        before_sha = None
        after_sha = None

        if not self.config.GITHUB_EVENT_PATH:
            return None, None

        try:
            with open(self.config.GITHUB_EVENT_PATH, "rb") as f:
                # Use ijson's kvitems to iterate over top-level key-value pairs
                # This is memory-efficient even for large JSON files
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

        except Exception as e:
            self.debug(f"ijson parsing failed: {e}, falling back to regex")
            return self._extract_shas_with_regex()

    def _extract_shas_with_regex(self) -> tuple[str | None, str | None]:
        """
        Extract SHAs using regex line-by-line parsing (fallback method).

        Returns:
            Tuple of (before_sha, after_sha) or (None, None) if not found
        """
        before_sha = None
        after_sha = None
        line_count = 0

        try:
            if not self.config.GITHUB_EVENT_PATH:
                return None, None

            # Read file line by line looking for before/after fields
            # This is safe because GitHub event payloads are well-formatted JSON
            with open(self.config.GITHUB_EVENT_PATH) as f:
                for line in f:
                    line_count += 1
                    line = line.strip()

                    # Look for "before": "sha..." pattern
                    if '"before"' in line and before_sha is None:
                        match = self._BEFORE_SHA_PATTERN.search(line)
                        if match:
                            before_sha = match.group(1)
                            self.debug(f"Found before SHA: {before_sha[:7]}")

                    # Look for "after": "sha..." pattern
                    if '"after"' in line and after_sha is None:
                        match = self._AFTER_SHA_PATTERN.search(line)
                        if match:
                            after_sha = match.group(1)
                            self.debug(f"Found after SHA: {after_sha[:7]}")

                    # Stop once we have both
                    if before_sha and after_sha:
                        break

                    # Safety: don't read excessive lines
                    if line_count > MAX_EVENT_LINES_TO_SCAN:
                        self.warning(f"Event payload too large (>{MAX_EVENT_LINES_TO_SCAN} lines), stopping search")
                        break

            return before_sha, after_sha

        except Exception as e:
            self.debug(f"Regex parsing failed: {e}")
            return None, None

    def _extract_pull_request(self) -> list[str]:
        """
        Extract changed files for pull request events.

        Determines best strategy (API vs git) and delegates to appropriate method.

        Returns:
            List of changed file paths
        """
        strategy = self._determine_pr_strategy()

        if strategy == "api":
            return self._extract_pr_api()
        if strategy == "git":
            return self._extract_pr_git()
        self.warning("No viable strategy for detecting PR changed files")
        return []

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
                with open(self.config.GITHUB_EVENT_PATH) as f:
                    event = json.load(f)
                pr_number = event.get("pull_request", {}).get("number")
                if pr_number:
                    self.debug(f"Got PR number from event payload: {pr_number}")
                    return int(pr_number)
            except Exception as e:
                self.debug(f"Failed to extract PR number from event: {e}")

        return None

    def _extract_pr_api(self) -> list[str]:
        """Extract PR changed files using GitHub API."""
        if not self.github_api:
            self.error("GitHub API client not available")
            return []

        try:
            pr_number = self._get_pr_number()
            if not pr_number:
                self.error("Cannot extract PR number from GITHUB_REF or event payload")
                return []

            self.debug(f"Fetching files for PR #{pr_number} via GitHub API")
            files = self.github_api.get_pr_files(
                self.config.GITHUB_REPOSITORY,
                pr_number
            )
            return files

        except Exception as e:
            self.error("Failed to fetch PR files via API", e)
            return []

    def _extract_pr_git(self) -> list[str]:
        """
        Extract PR changed files using git commands.

        This method:
        - Handles shallow clones by fetching base branch if needed
        - Uses three-dot diff (base...head) to show PR changes
        - Falls back through multiple strategies if needed

        Returns:
            List of changed file paths
        """
        if not self.git_ops:
            self.error("Git operations handler not available")
            return []

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
            files = self.git_ops.diff_branches(f"origin/{base_ref}", "HEAD")

            if files:
                return files

            # If no files found, try fallback strategies
            self.debug("No files from base diff, trying fallback")
            return self._extract_pr_git_fallback()

        except Exception as e:
            self.error("Failed to extract PR files via git", e)
            return []

    def _extract_pr_git_fallback(self) -> list[str]:
        """
        Fallback strategies for PR file detection when base branch unavailable.

        Tries multiple strategies in order:
        1. Diff against HEAD^1 (first parent)
        2. Show files in HEAD commit
        3. Diff-tree for HEAD

        Returns:
            List of changed file paths
        """
        if not self.git_ops:
            self.error("Git operations handler not available for fallback")
            return []

        strategies = [
            ("HEAD^1", lambda: self.git_ops.diff_commits("HEAD^1", "HEAD")),  # type: ignore[union-attr]
            ("git show", lambda: self._get_files_from_show()),
            ("diff-tree", lambda: self.git_ops.get_commit_files("HEAD")),  # type: ignore[union-attr]
        ]

        for strategy_name, strategy_func in strategies:
            try:
                self.debug(f"Trying fallback strategy: {strategy_name}")
                files = strategy_func()
                if files:
                    self.debug(f"Got {len(files)} files from {strategy_name}")
                    return files
            except Exception as e:
                self.debug(f"Strategy {strategy_name} failed: {e}")

        self.warning("All PR git fallback strategies failed")
        return []

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
