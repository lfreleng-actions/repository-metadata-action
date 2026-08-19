# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Commit and branch diffing operations for GitOperations.

Split out of git_operations.py so each module stays focused:
this mixin holds the diffing and added/modified/removed
categorization logic, while git_operations.py keeps repository
state and plumbing (commit metadata, fetch, deepen).
"""

import logging
from typing import TYPE_CHECKING

from git import GitCommandError

if TYPE_CHECKING:
    from collections.abc import Iterable

    from git import Repo
    from git.diff import Diff


class GitDiffOperationsMixin:
    """Diffing methods mixed into GitOperations.

    Relies on the host class providing ``repo``, ``logger`` and
    ``_merge_base_cache``.
    """

    logger: logging.Logger
    _merge_base_cache: dict

    if TYPE_CHECKING:

        @property
        def repo(self) -> "Repo | None": ...

    @staticmethod
    def _collect_diff_paths(diffs: "Iterable[Diff]") -> list[str]:
        """Collect unique changed file paths from a diff index, sorted."""
        files = []
        for diff in diffs:
            if diff.a_path:
                files.append(diff.a_path)
            if diff.b_path and diff.b_path != diff.a_path:
                files.append(diff.b_path)
        return sorted(set(files))

    @staticmethod
    def _categorize_diffs(diffs: "Iterable[Diff]") -> dict[str, list[str]]:
        """Categorize a diff index into added/modified/removed paths.

        Renames count as modifications of the new path.
        """
        added = []
        modified = []
        removed = []
        for diff in diffs:
            if diff.new_file:
                if diff.b_path:
                    added.append(diff.b_path)
            elif diff.deleted_file:
                if diff.a_path:
                    removed.append(diff.a_path)
            elif diff.renamed_file:
                if diff.b_path:
                    modified.append(diff.b_path)
            elif diff.b_path:
                modified.append(diff.b_path)
            elif diff.a_path:
                modified.append(diff.a_path)
        return {
            "added": sorted(set(added)),
            "modified": sorted(set(modified)),
            "removed": sorted(set(removed)),
        }

    def diff_commits(self, from_sha: str, to_sha: str) -> list[str]:
        """
        Get files changed between two commits.

        Args:
            from_sha: Starting commit SHA
            to_sha: Ending commit SHA

        Returns:
            List of file paths changed between commits
        """
        if not self.repo:
            self.logger.error("No git repository available")
            return []

        try:
            from_commit = self.repo.commit(from_sha)
            to_commit = self.repo.commit(to_sha)

            return self._collect_diff_paths(from_commit.diff(to_commit))

        except (GitCommandError, ValueError) as e:
            self.logger.error(f"Failed to diff {from_sha}..{to_sha}: {e}")
            return []

    def diff_branches(self, base: str, head: str) -> list[str]:
        """
        Get files changed between branches using three-dot diff.

        This shows changes in head that are not in base (typical for PRs).

        Args:
            base: Base branch ref
            head: Head branch ref

        Returns:
            List of file paths changed between branches
        """
        if not self.repo:
            self.logger.error("No git repository available")
            return []

        try:
            # Get the merge base (common ancestor)
            base_commit = self.repo.commit(base)
            head_commit = self.repo.commit(head)

            cache_key = (base, head)
            if cache_key in self._merge_base_cache:
                merge_bases = self._merge_base_cache[cache_key]
                self.logger.debug(f"Using cached merge base for {base}...{head}")
            else:
                # Find merge base (can be expensive on large repos)
                merge_bases = self.repo.merge_base(base_commit, head_commit)
                # Cache the result for future use
                self._merge_base_cache[cache_key] = merge_bases
                self.logger.debug(f"Computed and cached merge base for {base}...{head}")
            if not merge_bases:
                self.logger.warning(f"No merge base found between {base} and {head}")
                # Fall back to two-dot diff using existing commits
                return self._collect_diff_paths(base_commit.diff(head_commit))

            # Three-dot diff: changes from merge-base to head
            return self._collect_diff_paths(merge_bases[0].diff(head_commit))

        except (GitCommandError, ValueError) as e:
            self.logger.error(f"Failed to diff {base}...{head}: {e}")
            return []

    def get_commit_files_categorized(self, sha: str = "HEAD") -> dict[str, list[str]]:
        """
        Get categorized list of files changed in a specific commit.

        Args:
            sha: Commit SHA or ref (defaults to HEAD)

        Returns:
            Dict with keys 'added', 'modified', 'removed' containing file paths
        """
        if not self.repo:
            self.logger.error("No git repository available")
            return {"added": [], "modified": [], "removed": []}

        try:
            commit = self.repo.commit(sha)

            # Get files changed in this commit compared to its parent(s)
            if not commit.parents:
                # Initial commit - all files are added
                all_files = [
                    str(item.path)  # type: ignore[union-attr]
                    for item in commit.tree.traverse()
                    if hasattr(item, "path")
                ]
                return {"added": sorted(all_files), "modified": [], "removed": []}

            # Use diff to parent to get changed files with status
            parent = commit.parents[0]
            return self._categorize_diffs(parent.diff(commit))

        except (GitCommandError, ValueError, IndexError) as e:
            self.logger.error(f"Failed to get categorized commit files for {sha}: {e}")
            return {"added": [], "modified": [], "removed": []}

    def diff_commits_categorized(self, from_sha: str, to_sha: str) -> dict[str, list[str]]:
        """
        Get categorized files changed between two commits.

        Args:
            from_sha: Starting commit SHA
            to_sha: Ending commit SHA

        Returns:
            Dict with keys 'added', 'modified', 'removed' containing file paths
        """
        if not self.repo:
            self.logger.error("No git repository available")
            return {"added": [], "modified": [], "removed": []}

        try:
            from_commit = self.repo.commit(from_sha)
            to_commit = self.repo.commit(to_sha)

            return self._categorize_diffs(from_commit.diff(to_commit))

        except (GitCommandError, ValueError) as e:
            self.logger.error(f"Failed to get categorized diff {from_sha}..{to_sha}: {e}")
            return {"added": [], "modified": [], "removed": []}

    def diff_branches_categorized(self, base: str, head: str) -> dict[str, list[str]]:
        """
        Get categorized files changed between branches using three-dot diff.

        This shows changes in head that are not in base (typical for PRs).

        Args:
            base: Base branch ref
            head: Head branch ref

        Returns:
            Dict with keys 'added', 'modified', 'removed' containing file paths
        """
        if not self.repo:
            self.logger.error("No git repository available")
            return {"added": [], "modified": [], "removed": []}

        try:
            # Get the merge base (common ancestor)
            base_commit = self.repo.commit(base)
            head_commit = self.repo.commit(head)

            cache_key = f"{base}...{head}"
            if cache_key in self._merge_base_cache:
                merge_base = self._merge_base_cache[cache_key]
                self.logger.debug(f"Using cached merge base for {base}...{head}")
            else:
                merge_bases = self.repo.merge_base(base_commit, head_commit)
                self._merge_base_cache[cache_key] = merge_bases[0] if merge_bases else None
                merge_base = self._merge_base_cache[cache_key]
                self.logger.debug(f"Computed and cached merge base for {base}...{head}")

            if not merge_base:
                self.logger.warning(f"No merge base found between {base} and {head}")
                # Fall back to two-dot diff
                diffs = base_commit.diff(head_commit)
            else:
                # Three-dot diff: changes from merge-base to head
                diffs = merge_base.diff(head_commit)

            return self._categorize_diffs(diffs)

        except (GitCommandError, ValueError) as e:
            self.logger.error(f"Failed to get categorized diff {base}...{head}: {e}")
            return {"added": [], "modified": [], "removed": []}
