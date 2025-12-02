# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Changed files last commit detection.
Extracts files changed in the most recent commit (HEAD).
"""

from typing import TYPE_CHECKING

from ..models import ChangedFilesMetadata
from .base import BaseExtractor

if TYPE_CHECKING:
    from ..config import Config
    from ..git_operations import GitOperations


class ChangedFilesLastCommitExtractor(BaseExtractor):
    """Detects changed files in the last commit (HEAD)."""

    def __init__(
        self,
        config: "Config",
        git_ops: "GitOperations | None" = None,
        **kwargs
    ):
        """
        Initialize changed files last commit extractor.

        Args:
            config: Configuration object
            git_ops: Optional git operations handler
            **kwargs: Additional arguments passed to base class
        """
        super().__init__(config, **kwargs)
        self.git_ops = git_ops

    def extract(self) -> ChangedFilesMetadata:
        """
        Extract changed files from the last commit (HEAD).

        Returns:
            ChangedFilesMetadata object with list of changed files and categories
        """
        self.debug("Detecting changed files in last commit (HEAD)")

        files: list[str] = []
        added: list[str] = []
        modified: list[str] = []
        removed: list[str] = []

        # Only attempt extraction if we have git operations available
        if not self.git_ops or not self.git_ops.has_git_repo():
            self.debug("No git repository available, skipping last commit file detection")
            return ChangedFilesMetadata(
                count=0,
                files=[],
                added=[],
                modified=[],
                removed=[]
            )

        try:
            # Get categorized files from the last commit
            categorized = self.git_ops.get_commit_files_categorized("HEAD")

            added = categorized.get("added", [])
            modified = categorized.get("modified", [])
            removed = categorized.get("removed", [])

            # Combine all files
            files = sorted(set(added + modified + removed))

            if files:
                self.info(
                    f"Detected {len(files)} changed files in last commit "
                    f"({len(added)} added, {len(modified)} modified, {len(removed)} removed)"
                )
            else:
                self.debug("No changed files detected in last commit")

        except Exception as e:
            self.logger.warning(f"Failed to get changed files from last commit: {e}")
            # Return empty metadata on failure
            return ChangedFilesMetadata(
                count=0,
                files=[],
                added=[],
                modified=[],
                removed=[]
            )

        return ChangedFilesMetadata(
            count=len(files),
            files=files,
            added=added,
            modified=modified,
            removed=removed
        )
