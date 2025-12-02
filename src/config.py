# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Configuration module for repository metadata action.
Handles environment variables, defaults, and validation.
"""

import logging
import os
import re
from pathlib import Path
from typing import Literal

from .constants import DEFAULT_GIT_FETCH_DEPTH
from .exceptions import ConfigurationError, ValidationError
from .validators import InputValidator


class Config:
    """Configuration singleton for the action."""

    # Type hints for optional attributes
    GITHUB_STEP_SUMMARY: Path | None
    GITHUB_EVENT_PATH: Path | None
    GITHUB_REF: str | None
    GITHUB_REF_NAME: str | None
    GITHUB_REF_TYPE: str | None
    GITHUB_BASE_REF: str | None
    GITHUB_HEAD_REF: str | None
    GITHUB_ACTOR_ID: int | str | None  # Can be str if validation fails
    REPO_VISIBILITY: str | None
    DEFAULT_BRANCH: str | None
    GITHUB_TOKEN: str | None

    def __init__(self):
        """Initialize configuration from environment."""
        self._load_required_vars()
        self._load_optional_vars()
        self._load_action_inputs()
        self._validate()

    def _load_required_vars(self) -> None:
        """Load and validate required environment variables."""
        # Load and validate GITHUB_REPOSITORY
        repo = os.environ.get("GITHUB_REPOSITORY")
        if not repo:
            raise ConfigurationError("Required environment variable 'GITHUB_REPOSITORY' is not set")
        try:
            self.GITHUB_REPOSITORY = InputValidator.validate_repository_name(repo)
        except ValidationError as e:
            raise ConfigurationError(f"Invalid GITHUB_REPOSITORY: {e}")

        # Load and validate GITHUB_SHA
        sha = os.environ.get("GITHUB_SHA")
        if not sha:
            raise ConfigurationError("Required environment variable 'GITHUB_SHA' is not set")
        try:
            self.GITHUB_SHA = InputValidator.validate_sha(sha, "GITHUB_SHA")
        except ValidationError as e:
            raise ConfigurationError(f"Invalid GITHUB_SHA: {e}")

        # Load and validate GITHUB_REPOSITORY_OWNER
        owner = os.environ.get("GITHUB_REPOSITORY_OWNER")
        if not owner:
            raise ConfigurationError("Required environment variable 'GITHUB_REPOSITORY_OWNER' is not set")
        # Owner is part of repository name, basic sanitization
        if not owner or len(owner) > 39 or not re.match(r"^[a-zA-Z0-9_.-]+$", owner):
            raise ConfigurationError(f"Invalid GITHUB_REPOSITORY_OWNER: {owner}")
        self.GITHUB_REPOSITORY_OWNER = owner

        # Load and validate GITHUB_ACTOR
        actor = os.environ.get("GITHUB_ACTOR")
        if not actor:
            raise ConfigurationError("Required environment variable 'GITHUB_ACTOR' is not set")
        try:
            self.GITHUB_ACTOR = InputValidator.validate_actor_name(actor)
        except ValidationError as e:
            raise ConfigurationError(f"Invalid GITHUB_ACTOR: {e}")

        # Load and validate GITHUB_EVENT_NAME
        event = os.environ.get("GITHUB_EVENT_NAME")
        if not event:
            raise ConfigurationError("Required environment variable 'GITHUB_EVENT_NAME' is not set")
        try:
            self.GITHUB_EVENT_NAME = InputValidator.validate_event_name(event)
        except ValidationError as e:
            raise ConfigurationError(f"Invalid GITHUB_EVENT_NAME: {e}")

        # Load and validate GITHUB_OUTPUT path
        output = os.environ.get("GITHUB_OUTPUT")
        if not output:
            raise ConfigurationError("Required environment variable 'GITHUB_OUTPUT' is not set")
        # GITHUB_OUTPUT is expected to be an absolute path in GitHub Actions
        # Just check for dangerous characters, don't validate as path component
        if "\x00" in output or "\n" in output or "\r" in output:
            raise ConfigurationError("Invalid GITHUB_OUTPUT: contains null bytes or newlines")
        self.GITHUB_OUTPUT = Path(output)

        # GITHUB_STEP_SUMMARY may not exist in all environments
        step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
        self.GITHUB_STEP_SUMMARY: Path | None = Path(step_summary) if step_summary else None

        # GITHUB_EVENT_PATH is required for some features
        event_path = os.environ.get("GITHUB_EVENT_PATH")
        self.GITHUB_EVENT_PATH: Path | None = Path(event_path) if event_path else None

    def _load_optional_vars(self) -> None:
        """Load optional environment variables with defaults."""
        # GitHub context variables - validate ref names
        github_ref = os.environ.get("GITHUB_REF")
        if github_ref:
            try:
                self.GITHUB_REF = InputValidator.validate_ref_name(github_ref, "GITHUB_REF")
            except ValidationError as e:
                # Log but don't fail for optional vars
                logging.warning(f"GITHUB_REF validation failed: {e}, using raw value")
                self.GITHUB_REF = github_ref
        else:
            self.GITHUB_REF = None

        github_ref_name = os.environ.get("GITHUB_REF_NAME")
        if github_ref_name:
            try:
                self.GITHUB_REF_NAME = InputValidator.validate_ref_name(github_ref_name, "GITHUB_REF_NAME")
            except ValidationError as e:
                logging.warning(f"GITHUB_REF_NAME validation failed: {e}, using raw value")
                self.GITHUB_REF_NAME = github_ref_name
        else:
            self.GITHUB_REF_NAME = None

        # REF_TYPE should be 'branch' or 'tag'
        ref_type = os.environ.get("GITHUB_REF_TYPE")
        if ref_type and ref_type not in ("branch", "tag"):
            raise ConfigurationError(f"Invalid GITHUB_REF_TYPE: {ref_type}")
        self.GITHUB_REF_TYPE = ref_type

        github_base_ref = os.environ.get("GITHUB_BASE_REF")
        if github_base_ref:
            try:
                self.GITHUB_BASE_REF = InputValidator.validate_ref_name(github_base_ref, "GITHUB_BASE_REF")
            except ValidationError as e:
                logging.warning(f"GITHUB_BASE_REF validation failed: {e}, using raw value")
                self.GITHUB_BASE_REF = github_base_ref
        else:
            self.GITHUB_BASE_REF = None

        github_head_ref = os.environ.get("GITHUB_HEAD_REF")
        if github_head_ref:
            try:
                self.GITHUB_HEAD_REF = InputValidator.validate_ref_name(github_head_ref, "GITHUB_HEAD_REF")
            except ValidationError as e:
                logging.warning(f"GITHUB_HEAD_REF validation failed: {e}, using raw value")
                self.GITHUB_HEAD_REF = github_head_ref
        else:
            self.GITHUB_HEAD_REF = None

        # Actor ID should be numeric
        actor_id = os.environ.get("GITHUB_ACTOR_ID")
        if actor_id:
            try:
                self.GITHUB_ACTOR_ID: int | None = InputValidator.validate_integer(actor_id, "GITHUB_ACTOR_ID", min_val=1)
            except ValidationError as e:
                logging.warning(f"GITHUB_ACTOR_ID validation failed: {e}, using raw value")
                self.GITHUB_ACTOR_ID = actor_id
        else:
            self.GITHUB_ACTOR_ID = None

        # Runner variables - RUNNER_TEMP is expected to be absolute path
        runner_temp = os.environ.get("RUNNER_TEMP", "/tmp")
        # Just check for dangerous characters, don't validate as path component
        if runner_temp and ("\x00" in runner_temp or "\n" in runner_temp or "\r" in runner_temp):
            # Fall back to /tmp if contains dangerous characters
            self.RUNNER_TEMP = Path("/tmp")
        else:
            self.RUNNER_TEMP = Path(runner_temp).resolve()

        # Repository visibility (from github.event.repository.visibility)
        self.REPO_VISIBILITY = os.environ.get("REPO_VISIBILITY")

        # PR-specific (from github.event.pull_request.head.repo.fork)
        pr_fork = os.environ.get("PR_HEAD_REPO_FORK", "false").lower()
        self.PR_HEAD_REPO_FORK = pr_fork in ("true", "1", "yes")

        # Default branch (from github.event.repository.default_branch)
        self.DEFAULT_BRANCH = os.environ.get("DEFAULT_BRANCH")

    def _load_action_inputs(self) -> None:
        """Load action-specific inputs from environment."""
        # GitHub token for API access
        self.GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN_INPUT") or os.environ.get("GITHUB_TOKEN")

        # Debug mode
        debug_str = os.environ.get("DEBUG_MODE", "false").lower()
        self.DEBUG_MODE = debug_str in ("true", "1", "yes")

        # GitHub summary (renamed from GENERATE_SUMMARY for clarity)
        # Support both names for backward compatibility
        github_summary_str = os.environ.get("GITHUB_SUMMARY") or os.environ.get("GENERATE_SUMMARY") or "false"
        self.GITHUB_SUMMARY = github_summary_str.lower() in ("true", "1", "yes")

        # Gerrit summary (independent of GitHub summary)
        gerrit_summary_str = os.environ.get("GERRIT_SUMMARY", "false").lower()
        self.GERRIT_SUMMARY = gerrit_summary_str in ("true", "1", "yes")

        # Files summary (independent of GitHub summary)
        files_summary_str = os.environ.get("FILES_SUMMARY", "false").lower()
        self.FILES_SUMMARY = files_summary_str in ("true", "1", "yes")

        # Artifact upload
        artifact_str = os.environ.get("ARTIFACT_UPLOAD", "false").lower()
        self.ARTIFACT_UPLOAD = artifact_str in ("true", "1", "yes")

        # Gerrit include comment
        gerrit_comment_str = os.environ.get("GERRIT_INCLUDE_COMMENT", "false").lower()
        self.GERRIT_INCLUDE_COMMENT = gerrit_comment_str in ("true", "1", "yes")

        # Change detection method
        change_detection = os.environ.get("CHANGE_DETECTION", "auto").lower()
        if change_detection not in ("auto", "git", "github_api"):
            change_detection = "auto"
        self.CHANGE_DETECTION: Literal["auto", "git", "github_api"] = change_detection  # type: ignore[assignment]

        # Git fetch depth
        depth_str = os.environ.get("GIT_FETCH_DEPTH", str(DEFAULT_GIT_FETCH_DEPTH))
        try:
            self.GIT_FETCH_DEPTH = InputValidator.validate_integer(
                depth_str, "GIT_FETCH_DEPTH", min_val=1, max_val=10000
            )
        except ValidationError as e:
            logging.warning(f"Invalid GIT_FETCH_DEPTH '{depth_str}': {e}, using default {DEFAULT_GIT_FETCH_DEPTH}")
            self.GIT_FETCH_DEPTH = DEFAULT_GIT_FETCH_DEPTH

        # Artifact formats
        formats_str = os.environ.get("ARTIFACT_FORMATS", "json,yaml")
        self.ARTIFACT_FORMATS: list[str] = [
            fmt.strip().lower()
            for fmt in formats_str.split(",")
            if fmt.strip()
        ]

        # Gerrit-specific environment variables
        self.GERRIT_BRANCH = os.environ.get("GERRIT_BRANCH")
        self.GERRIT_CHANGE_ID = os.environ.get("GERRIT_CHANGE_ID")
        self.GERRIT_CHANGE_NUMBER = os.environ.get("GERRIT_CHANGE_NUMBER")
        self.GERRIT_CHANGE_URL = os.environ.get("GERRIT_CHANGE_URL")
        self.GERRIT_EVENT_TYPE = os.environ.get("GERRIT_EVENT_TYPE")
        self.GERRIT_PATCHSET_NUMBER = os.environ.get("GERRIT_PATCHSET_NUMBER")
        self.GERRIT_PATCHSET_REVISION = os.environ.get("GERRIT_PATCHSET_REVISION")
        self.GERRIT_PROJECT = os.environ.get("GERRIT_PROJECT")
        self.GERRIT_REFSPEC = os.environ.get("GERRIT_REFSPEC")
        self.GERRIT_COMMENT = os.environ.get("GERRIT_COMMENT")

    def _validate(self) -> None:
        """Validate configuration consistency."""
        # Ensure GITHUB_OUTPUT is writable
        try:
            # Check if parent directory exists
            if not self.GITHUB_OUTPUT.parent.exists():
                raise ConfigurationError(
                    f"GITHUB_OUTPUT parent directory does not exist: {self.GITHUB_OUTPUT.parent}"
                )
        except Exception as e:
            raise ConfigurationError(f"Cannot validate GITHUB_OUTPUT path: {e}")

        # Additional validation already handled in _load_required_vars


# Global config instance
_config_instance: Config | None = None


def get_config() -> Config:
    """Get or create the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
