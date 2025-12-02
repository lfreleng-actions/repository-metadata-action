# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Pydantic models for structured metadata.
Provides validation, serialization, and type safety.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .validators import InputValidator


class RepositoryMetadata(BaseModel):
    """Repository information model."""
    owner: str
    name: str
    full_name: str
    is_public: bool = False
    is_private: bool = False

    @model_validator(mode="after")
    def validate_visibility(self):
        """Ensure is_public and is_private are mutually exclusive."""
        if self.is_public and self.is_private:
            raise ValueError("Repository cannot be both public and private")
        return self


class EventMetadata(BaseModel):
    """Event type information model."""
    name: str
    is_tag_push: bool = False
    is_branch_push: bool = False
    is_pull_request: bool = False
    is_release: bool = False
    is_schedule: bool = False
    is_workflow_dispatch: bool = False
    tag_push_event: bool = False  # True for version tags (v*.*.*)


class RefMetadata(BaseModel):
    """Reference (branch/tag) information model."""
    branch_name: str | None = None
    tag_name: str | None = None
    is_default_branch: bool = False
    is_main_branch: bool = False


class CommitMetadata(BaseModel):
    """Commit information model."""
    sha: str
    sha_short: str
    message: str | None = None
    author: str | None = None

    @field_validator("sha_short", mode="before")
    @classmethod
    def compute_short_sha(cls, v, info):
        """Auto-compute short SHA from full SHA if not provided."""
        if not v and "sha" in info.data:
            return info.data["sha"][:7]
        return v

    @field_validator("sha_short")
    @classmethod
    def validate_short_sha_length(cls, v):
        """Ensure short SHA is exactly 7 characters."""
        if len(v) != 7:
            raise ValueError(f"Short SHA must be 7 characters, got {len(v)}")
        return v


class PullRequestMetadata(BaseModel):
    """Pull request information model."""
    number: int | None = None
    source_branch: str | None = None
    target_branch: str | None = None
    commits_count: int | None = None
    is_fork: bool = False


class ActorMetadata(BaseModel):
    """Actor (user who triggered action) information model."""
    name: str
    id: int | None = None


class CacheMetadata(BaseModel):
    """Cache key information model."""
    key: str
    restore_key: str


class ChangedFilesMetadata(BaseModel):
    """Changed files information model."""
    count: int = 0
    files: list[str] = Field(default_factory=list)
    added: list[str] = Field(default_factory=list)
    added_count: int = 0
    modified: list[str] = Field(default_factory=list)
    modified_count: int = 0
    removed: list[str] = Field(default_factory=list)
    removed_count: int = 0

    @model_validator(mode="after")
    def sync_counts(self):
        """Ensure counts match list lengths."""
        self.count = len(self.files)
        self.added_count = len(self.added)
        self.modified_count = len(self.modified)
        self.removed_count = len(self.removed)
        return self


class GerritMetadata(BaseModel):
    """Gerrit integration metadata model."""
    branch: str = Field(default="")
    change_id: str = Field(default="")
    change_number: str = Field(default="")
    change_url: str = Field(default="")
    event_type: str = Field(default="")
    patchset_number: str = Field(default="")
    patchset_revision: str = Field(default="")
    project: str = Field(default="")
    refspec: str = Field(default="")
    comment: str = Field(default="")
    source: str = Field(default="")


class CompleteMetadata(BaseModel):
    """Complete metadata model combining all components."""
    repository: RepositoryMetadata
    event: EventMetadata
    ref: RefMetadata
    commit: CommitMetadata
    pull_request: PullRequestMetadata
    actor: ActorMetadata
    cache: CacheMetadata
    changed_files: ChangedFilesMetadata
    changed_files_last_commit: ChangedFilesMetadata
    gerrit_environment: GerritMetadata

    def to_action_outputs(self, include_comment: bool = False) -> dict[str, str]:
        """
        Convert to GitHub Action outputs format.
        All values must be strings for GITHUB_OUTPUT.
        Values are sanitized to remove control characters.

        Args:
            include_comment: Whether to include Gerrit comment field (default: False for security)
        """
        outputs = {}

        # Repository outputs
        outputs["repository_owner"] = self.repository.owner
        outputs["repository_name"] = self.repository.name
        outputs["repository_full_name"] = self.repository.full_name
        outputs["is_public"] = str(self.repository.is_public).lower()
        outputs["is_private"] = str(self.repository.is_private).lower()

        # Event outputs
        outputs["event_name"] = self.event.name
        outputs["is_tag_push"] = str(self.event.is_tag_push).lower()
        outputs["is_branch_push"] = str(self.event.is_branch_push).lower()
        outputs["is_pull_request"] = str(self.event.is_pull_request).lower()
        outputs["is_release"] = str(self.event.is_release).lower()
        outputs["is_schedule"] = str(self.event.is_schedule).lower()
        outputs["is_workflow_dispatch"] = str(self.event.is_workflow_dispatch).lower()
        outputs["tag_push_event"] = str(self.event.tag_push_event).lower()

        # Ref outputs
        outputs["branch_name"] = self.ref.branch_name or ""
        outputs["tag_name"] = self.ref.tag_name or ""
        outputs["is_default_branch"] = str(self.ref.is_default_branch).lower()
        outputs["is_main_branch"] = str(self.ref.is_main_branch).lower()

        # Commit outputs
        outputs["commit_sha"] = self.commit.sha
        outputs["commit_sha_short"] = self.commit.sha_short
        outputs["commit_message"] = self.commit.message or ""
        outputs["commit_author"] = self.commit.author or ""

        # PR outputs
        outputs["pr_number"] = str(self.pull_request.number or "")
        outputs["pr_source_branch"] = self.pull_request.source_branch or ""
        outputs["pr_target_branch"] = self.pull_request.target_branch or ""
        outputs["pr_commits_count"] = str(self.pull_request.commits_count or "")
        outputs["is_fork"] = str(self.pull_request.is_fork).lower()

        # Actor outputs
        outputs["actor"] = self.actor.name
        outputs["actor_id"] = str(self.actor.id or "")

        # Cache outputs
        outputs["cache_key"] = self.cache.key
        outputs["cache_restore_key"] = self.cache.restore_key

        # Changed files outputs (newline-delimited for multi-line output)
        outputs["changed_files"] = "\n".join(self.changed_files.files)
        outputs["changed_files_count"] = str(self.changed_files.count)
        outputs["changed_files_added"] = "\n".join(self.changed_files.added)
        outputs["changed_files_added_count"] = str(self.changed_files.added_count)
        outputs["changed_files_modified"] = "\n".join(self.changed_files.modified)
        outputs["changed_files_modified_count"] = str(self.changed_files.modified_count)
        outputs["changed_files_removed"] = "\n".join(self.changed_files.removed)
        outputs["changed_files_removed_count"] = str(self.changed_files.removed_count)

        # Changed files last commit outputs (newline-delimited for multi-line output)
        outputs["changed_files_last_commit"] = "\n".join(self.changed_files_last_commit.files)
        outputs["changed_files_last_commit_count"] = str(self.changed_files_last_commit.count)
        outputs["changed_files_last_commit_added"] = "\n".join(self.changed_files_last_commit.added)
        outputs["changed_files_last_commit_added_count"] = str(self.changed_files_last_commit.added_count)
        outputs["changed_files_last_commit_modified"] = "\n".join(self.changed_files_last_commit.modified)
        outputs["changed_files_last_commit_modified_count"] = str(self.changed_files_last_commit.modified_count)
        outputs["changed_files_last_commit_removed"] = "\n".join(self.changed_files_last_commit.removed)
        outputs["changed_files_last_commit_removed_count"] = str(self.changed_files_last_commit.removed_count)

        # Gerrit output (as JSON string)
        # Always include Gerrit fields in output (even when empty)
        # Exclude 'source' field from output as it's for internal tracking only
        # Exclude 'comment' field unless explicitly requested (security)
        if self.gerrit_environment:
            exclude_fields = {"source"}
            if not include_comment:
                exclude_fields.add("comment")
            outputs["gerrit_json"] = self.gerrit_environment.model_dump_json(
                exclude_none=False,  # Keep empty string fields
                exclude=exclude_fields,
                by_alias=True
            )
        else:
            # This should not happen anymore since GerritExtractor always returns an object
            outputs["gerrit_json"] = "{}"

        # Sanitize all outputs to remove control characters
        # This prevents injection attacks via malicious commit messages, branch names, etc.
        sanitized_outputs = {}
        for key, value in outputs.items():
            sanitized_outputs[key] = InputValidator.sanitize_output_string(value)

        return sanitized_outputs

    def to_json(self, pretty: bool = False, include_comment: bool = False) -> str:
        """
        Convert to JSON string.

        Args:
            pretty: Whether to format JSON with indentation
            include_comment: Whether to include Gerrit comment field (default: False for security)

        Note: gerrit_environment fields use empty strings instead of None,
        so they will always be included in the output even when not populated.
        The comment field is excluded by default for security unless include_comment=True.
        """
        # Build exclude set for gerrit comment and source fields
        exclude = None
        if self.gerrit_environment:
            gerrit_exclude = {"source"}  # Always exclude internal 'source' field
            if not include_comment:
                gerrit_exclude.add("comment")
            exclude = {"gerrit_environment": gerrit_exclude}

        if pretty:
            return str(self.model_dump_json(
                exclude_none=False,  # Keep empty string fields for Gerrit
                exclude=exclude,
                indent=2,
                by_alias=True
            ))
        return str(self.model_dump_json(exclude_none=False, exclude=exclude, by_alias=True))

    def to_dict(self, include_comment: bool = False) -> dict[str, Any]:
        """
        Convert to dictionary.

        Args:
            include_comment: Whether to include Gerrit comment field (default: False for security)

        Note: gerrit_environment fields use empty strings instead of None,
        so they will always be included in the output even when not populated.
        The comment field is excluded by default for security unless include_comment=True.
        """
        # Build exclude set for gerrit comment and source fields
        exclude = None
        if self.gerrit_environment:
            gerrit_exclude = {"source"}  # Always exclude internal 'source' field
            if not include_comment:
                gerrit_exclude.add("comment")
            exclude = {"gerrit_environment": gerrit_exclude}

        return dict(self.model_dump(exclude_none=False, exclude=exclude, by_alias=True, mode="json"))
