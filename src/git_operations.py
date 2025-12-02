# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Git operations wrapper using GitPython library.
Provides a clean interface to git operations with proper error handling.
"""

import logging
from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, NoSuchPathError, Repo
from git.exc import GitError

from .exceptions import GitOperationError


class GitOperations:
    """Wrapper for git operations using GitPython."""

    def __init__(self, repo_path: Path = Path.cwd(), logger: logging.Logger | None = None):
        """
        Initialize git operations for a repository.

        Args:
            repo_path: Path to git repository (defaults to current directory)
            logger: Optional logger instance
        """
        self.repo_path = repo_path
        self.logger = logger or logging.getLogger(__name__)
        self._repo: Repo | None = None
        self._has_git: bool | None = None
        self._is_shallow: bool | None = None
        self._merge_base_cache: dict = {}  # Cache for merge base calculations

    @property
    def repo(self) -> Repo | None:
        """
        Lazy-load and cache the Repo object.

        Returns:
            Repo instance or None if not a git repository
        """
        if self._repo is None and self.has_git_repo():
            try:
                self._repo = Repo(self.repo_path)
                self.logger.debug(f"Initialized GitPython repo at {self.repo_path}")
            except (InvalidGitRepositoryError, NoSuchPathError) as e:
                self.logger.debug(f"Failed to initialize repo: {e}")
                return None
        return self._repo

    def has_git_repo(self) -> bool:
        """
        Check if current directory is a git repository.

        Returns:
            True if .git directory exists
        """
        if self._has_git is None:
            self._has_git = (self.repo_path / ".git").exists()
            if self._has_git:
                self.logger.debug("Git repository detected")
            else:
                self.logger.debug("No git repository found")
        return self._has_git

    def is_shallow_clone(self) -> bool:
        """
        Check if repository is a shallow clone.

        Returns:
            True if repository is shallow
        """
        if self._is_shallow is None:
            if not self.has_git_repo():
                self._is_shallow = False
                return False

            try:
                # Check for .git/shallow file which indicates a shallow clone
                shallow_file = self.repo_path / ".git" / "shallow"
                self._is_shallow = shallow_file.exists()

                if self._is_shallow:
                    self.logger.debug("Repository is a shallow clone")
                else:
                    self.logger.debug("Repository is not a shallow clone")
            except Exception as e:
                self.logger.debug(f"Failed to check shallow status: {e}")
                self._is_shallow = False

        return self._is_shallow

    def get_commit_message(self, sha: str = "HEAD") -> str | None:
        """
        Get commit message (subject line) for a specific commit.

        Args:
            sha: Commit SHA or ref (defaults to HEAD)

        Returns:
            Commit message (subject line) or None if unavailable
        """
        if not self.repo:
            self.logger.error("No git repository available")
            return None

        try:
            commit = self.repo.commit(sha)
            # Use GitPython's summary property for efficient subject extraction
            # This avoids loading and splitting the entire commit message
            if hasattr(commit, "summary"):
                message_raw = commit.summary
                if isinstance(message_raw, bytes):
                    message_raw = message_raw.decode("utf-8", errors="replace")
                message = message_raw.strip()
            else:
                msg = commit.message
                if isinstance(msg, bytes):
                    msg = msg.decode("utf-8", errors="replace")
                message = msg.split("\n")[0].strip()
            return message if message else None
        except (GitCommandError, ValueError) as e:
            self.logger.error(f"Failed to get commit message for {sha}: {e}")
            return None

    def get_commit_message_full(self, sha: str = "HEAD") -> str | None:
        """
        Get full commit message (including body) for a specific commit.

        Args:
            sha: Commit SHA or ref (defaults to HEAD)

        Returns:
            Full commit message or None if unavailable
        """
        if not self.repo:
            self.logger.error("No git repository available")
            return None

        try:
            commit = self.repo.commit(sha)
            msg = commit.message
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8", errors="replace")
            return msg.strip() if msg else None
        except (GitCommandError, ValueError) as e:
            self.logger.error(f"Failed to get full commit message for {sha}: {e}")
            return None

    def get_commit_author(self, sha: str = "HEAD") -> str | None:
        """
        Get commit author name for a specific commit.

        Args:
            sha: Commit SHA or ref (defaults to HEAD)

        Returns:
            Author name or None if unavailable
        """
        if not self.repo:
            self.logger.error("No git repository available")
            return None

        try:
            commit = self.repo.commit(sha)
            return commit.author.name if commit.author else None
        except (GitCommandError, ValueError) as e:
            self.logger.error(f"Failed to get commit author for {sha}: {e}")
            return None

    def get_commit_files(self, sha: str = "HEAD") -> list[str]:
        """
        Get list of files changed in a specific commit.

        Args:
            sha: Commit SHA or ref (defaults to HEAD)

        Returns:
            List of file paths changed in the commit
        """
        if not self.repo:
            self.logger.error("No git repository available")
            return []

        try:
            commit = self.repo.commit(sha)

            # Get files changed in this commit compared to its parent(s)
            if not commit.parents:
                # Initial commit - show all files
                return [str(item.path) for item in commit.tree.traverse() if hasattr(item, 'path')]  # type: ignore[union-attr]

            # Use diff to parent to get changed files
            parent = commit.parents[0]
            diffs = parent.diff(commit)

            files = []
            for diff in diffs:
                # Include both renamed files (a_path and b_path)
                if diff.a_path:
                    files.append(diff.a_path)
                if diff.b_path and diff.b_path != diff.a_path:
                    files.append(diff.b_path)

            return sorted(set(files))  # Remove duplicates and sort

        except (GitCommandError, ValueError, IndexError) as e:
            self.logger.error(f"Failed to get commit files for {sha}: {e}")
            return []

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

            # Get diff between commits
            diffs = from_commit.diff(to_commit)

            files = []
            for diff in diffs:
                if diff.a_path:
                    files.append(diff.a_path)
                if diff.b_path and diff.b_path != diff.a_path:
                    files.append(diff.b_path)

            return sorted(set(files))

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

            # Check cache for merge base
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
                diffs = base_commit.diff(head_commit)
                files = []
                for diff in diffs:
                    if diff.a_path:
                        files.append(diff.a_path)
                    if diff.b_path and diff.b_path != diff.a_path:
                        files.append(diff.b_path)
                return sorted(set(files))

            merge_base = merge_bases[0]

            # Three-dot diff: changes from merge-base to head
            diffs = merge_base.diff(head_commit)

            files = []
            for diff in diffs:
                if diff.a_path:
                    files.append(diff.a_path)
                if diff.b_path and diff.b_path != diff.a_path:
                    files.append(diff.b_path)

            return sorted(set(files))

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
                all_files = [str(item.path) for item in commit.tree.traverse() if hasattr(item, 'path')]  # type: ignore[union-attr]
                return {"added": sorted(all_files), "modified": [], "removed": []}

            # Use diff to parent to get changed files with status
            parent = commit.parents[0]
            diffs = parent.diff(commit)

            added = []
            modified = []
            removed = []

            for diff in diffs:
                if diff.new_file:
                    # File was added
                    if diff.b_path:
                        added.append(diff.b_path)
                elif diff.deleted_file:
                    # File was deleted
                    if diff.a_path:
                        removed.append(diff.a_path)
                elif diff.renamed_file:
                    # File was renamed - treat as modified
                    if diff.b_path:
                        modified.append(diff.b_path)
                else:
                    # File was modified
                    if diff.b_path:
                        modified.append(diff.b_path)
                    elif diff.a_path:
                        modified.append(diff.a_path)

            return {
                "added": sorted(set(added)),
                "modified": sorted(set(modified)),
                "removed": sorted(set(removed))
            }

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

            # Get diff between commits
            diffs = from_commit.diff(to_commit)

            added = []
            modified = []
            removed = []

            for diff in diffs:
                if diff.new_file:
                    # File was added
                    if diff.b_path:
                        added.append(diff.b_path)
                elif diff.deleted_file:
                    # File was deleted
                    if diff.a_path:
                        removed.append(diff.a_path)
                elif diff.renamed_file:
                    # File was renamed - treat as modified
                    if diff.b_path:
                        modified.append(diff.b_path)
                else:
                    # File was modified
                    if diff.b_path:
                        modified.append(diff.b_path)
                    elif diff.a_path:
                        modified.append(diff.a_path)

            return {
                "added": sorted(set(added)),
                "modified": sorted(set(modified)),
                "removed": sorted(set(removed))
            }

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

            # Check cache for merge base
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

            added = []
            modified = []
            removed = []

            for diff in diffs:
                if diff.new_file:
                    # File was added
                    if diff.b_path:
                        added.append(diff.b_path)
                elif diff.deleted_file:
                    # File was deleted
                    if diff.a_path:
                        removed.append(diff.a_path)
                elif diff.renamed_file:
                    # File was renamed - treat as modified
                    if diff.b_path:
                        modified.append(diff.b_path)
                else:
                    # File was modified
                    if diff.b_path:
                        modified.append(diff.b_path)
                    elif diff.a_path:
                        modified.append(diff.a_path)

            return {
                "added": sorted(set(added)),
                "modified": sorted(set(modified)),
                "removed": sorted(set(removed))
            }

        except (GitCommandError, ValueError) as e:
            self.logger.error(f"Failed to get categorized diff {base}...{head}: {e}")
            return {"added": [], "modified": [], "removed": []}

    def fetch_branch(self, branch: str, depth: int | None = None):
        """
        Fetch a specific branch from origin.

        Args:
            branch: Branch name (with origin/ prefix if needed)
            depth: Optional fetch depth for shallow clones

        Raises:
            GitOperationError: If fetch fails
        """
        if not self.repo:
            raise GitOperationError("No git repository available for fetch")

        try:
            # Parse branch name to handle origin/ prefix
            if branch.startswith("origin/"):
                branch_name = branch[7:]  # Remove 'origin/' prefix
            else:
                branch_name = branch

            # Build fetch refspec
            refspec = f"{branch_name}:refs/remotes/origin/{branch_name}"

            self.logger.debug(f"Fetching branch: {branch_name} (depth={depth})")

            # Fetch from origin
            origin = self.repo.remote("origin")
            if depth:
                origin.fetch(refspec, depth=depth)
            else:
                origin.fetch(refspec)

            # Invalidate cached shallow status as repository state may have changed
            self._is_shallow = None
            # Invalidate merge base cache as new history may have been fetched
            self._merge_base_cache.clear()

            self.logger.debug(f"Successfully fetched {branch_name}")

        except GitError as e:
            error_msg = f"Failed to fetch {branch}: {e}"
            self.logger.error(error_msg)
            raise GitOperationError(error_msg) from e

    def deepen(self, depth: int):
        """
        Deepen a shallow clone by fetching more history.

        Args:
            depth: Number of commits to deepen

        Raises:
            GitOperationError: If deepen fails
        """
        if not self.repo:
            raise GitOperationError("No git repository available for deepen")

        try:
            self.logger.debug(f"Deepening repository by {depth} commits")

            # Use git command directly for --deepen which GitPython doesn't expose cleanly
            self.repo.git.fetch(f"--deepen={depth}")

            # Invalidate cached shallow status as repository is no longer shallow (or less shallow)
            self._is_shallow = None
            # Invalidate merge base cache as repository history has changed
            self._merge_base_cache.clear()

            self.logger.debug("Successfully deepened repository")

        except GitCommandError as e:
            error_msg = f"Failed to deepen repository: {e}"
            self.logger.error(error_msg)
            raise GitOperationError(error_msg) from e

    def get_files_from_show(self, sha: str = "HEAD") -> list[str]:
        """
        Get changed files using 'git show' command.

        Useful for merge commits where diff-tree might not work well.

        Args:
            sha: Commit SHA or ref (defaults to HEAD)

        Returns:
            List of changed file paths
        """
        if not self.repo:
            self.logger.error("No git repository available")
            return []

        try:
            # Use git show with --name-only to get file names
            output = self.repo.git.show("--pretty=", "--name-only", sha)
            return [line.strip() for line in output.splitlines() if line.strip()]

        except GitCommandError as e:
            self.logger.error(f"Failed to get files from show for {sha}: {e}")
            return []
