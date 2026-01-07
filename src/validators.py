# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Input validation and sanitization utilities.
Provides security checks for environment variables and user inputs.
"""

import re
from pathlib import Path

from .constants import (
    MAX_OUTPUT_STRING_LENGTH,
    MAX_REF_NAME_LENGTH,
    MAX_REPOSITORY_NAME_LENGTH,
    MAX_REPOSITORY_OWNER_LENGTH,
)
from .exceptions import ValidationError


class InputValidator:
    """Validates and sanitizes inputs to prevent injection attacks."""

    # Allowed characters for various input types
    # SHA: hexadecimal (40 or 64 chars for SHA-1 or SHA-256)
    SHA_PATTERN = re.compile(r"^[a-f0-9]{7,64}$", re.IGNORECASE)

    # Repository name: owner/repo format
    REPO_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")

    # Branch/tag name: alphanumeric, dash, underscore, dot, forward slash
    REF_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9/_.-]+$")

    # Actor name: alphanumeric, dash, underscore, square brackets for bots (GitHub username rules)
    # Examples: "octocat", "dependabot[bot]", "github-actions[bot]"
    ACTOR_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\[\]-]){0,38}$")

    # Event name: lowercase alphanumeric with underscores
    EVENT_NAME_PATTERN = re.compile(r"^[a-z_]+$")

    # Path traversal patterns to detect
    PATH_TRAVERSAL_PATTERNS = [
        "..",      # Parent directory
        "~",       # Home directory
        "$",       # Variable expansion
        "`",       # Command substitution
        "\x00",    # Null byte
        "\n",      # Newline (in paths)
        "\r",      # Carriage return (in paths)
    ]

    @staticmethod
    def validate_sha(sha: str, field_name: str = "SHA") -> str:
        """
        Validate a git SHA.

        Args:
            sha: SHA string to validate
            field_name: Name of field for error messages

        Returns:
            Validated SHA string

        Raises:
            ValidationError: If SHA is invalid
        """
        if not sha:
            raise ValidationError(f"{field_name} cannot be empty")

        if not InputValidator.SHA_PATTERN.match(sha):
            raise ValidationError(
                f"{field_name} contains invalid characters. "
                f"Expected hexadecimal string (7-64 chars), got: {sha[:20]}..."
            )

        return sha

    @staticmethod
    def validate_repository_name(repo_name: str) -> str:
        """
        Validate a GitHub repository name (owner/repo format).

        Args:
            repo_name: Repository name to validate

        Returns:
            Validated repository name

        Raises:
            ValidationError: If repository name is invalid
        """
        if not repo_name:
            raise ValidationError("Repository name cannot be empty")

        if not InputValidator.REPO_NAME_PATTERN.match(repo_name):
            raise ValidationError(
                f"Repository name must be in 'owner/repo' format. "
                f"Got: {repo_name}"
            )

        # Additional length checks
        parts = repo_name.split("/")
        if len(parts[0]) > MAX_REPOSITORY_OWNER_LENGTH:
            raise ValidationError(f"Owner name too long: {parts[0]}")
        if len(parts[1]) > MAX_REPOSITORY_NAME_LENGTH:
            raise ValidationError(f"Repository name too long: {parts[1]}")

        return repo_name

    @staticmethod
    def validate_ref_name(ref_name: str, field_name: str = "ref") -> str:
        """
        Validate a git reference name (branch/tag).

        Args:
            ref_name: Reference name to validate
            field_name: Name of field for error messages

        Returns:
            Validated reference name

        Raises:
            ValidationError: If reference name is invalid
        """
        if not ref_name:
            raise ValidationError(f"{field_name} cannot be empty")

        if not InputValidator.REF_NAME_PATTERN.match(ref_name):
            raise ValidationError(
                f"{field_name} contains invalid characters. "
                f"Allowed: alphanumeric, dash, underscore, dot, slash. "
                f"Got: {ref_name[:50]}..."
            )

        # Check for suspicious patterns
        if ref_name.startswith("-"):
            raise ValidationError(f"{field_name} cannot start with dash")

        if "//" in ref_name:
            raise ValidationError(f"{field_name} cannot contain consecutive slashes")

        if len(ref_name) > MAX_REF_NAME_LENGTH:
            raise ValidationError(f"{field_name} is too long (max {MAX_REF_NAME_LENGTH} chars)")

        return ref_name

    @staticmethod
    def validate_actor_name(actor_name: str) -> str:
        """
        Validate a GitHub actor (username).

        Args:
            actor_name: Actor name to validate

        Returns:
            Validated actor name

        Raises:
            ValidationError: If actor name is invalid
        """
        if not actor_name:
            raise ValidationError("Actor name cannot be empty")

        if not InputValidator.ACTOR_NAME_PATTERN.match(actor_name):
            raise ValidationError(
                f"Actor name contains invalid characters. "
                f"Must be alphanumeric with dashes and square brackets (for bots), 1-39 chars. "
                f"Got: {actor_name}"
            )

        return actor_name

    @staticmethod
    def validate_event_name(event_name: str) -> str:
        """
        Validate a GitHub event name.

        Args:
            event_name: Event name to validate

        Returns:
            Validated event name

        Raises:
            ValidationError: If event name is invalid
        """
        if not event_name:
            raise ValidationError("Event name cannot be empty")

        if not InputValidator.EVENT_NAME_PATTERN.match(event_name):
            raise ValidationError(
                f"Event name contains invalid characters. "
                f"Expected lowercase with underscores. "
                f"Got: {event_name}"
            )

        # Whitelist of known GitHub event types
        known_events = {
            "push", "pull_request", "pull_request_target", "release",
            "schedule", "workflow_dispatch", "workflow_call", "repository_dispatch",
            "issue_comment", "issues", "create", "delete", "fork",
            "gollum", "merge_group", "milestone", "page_build",
            "project", "project_card", "project_column", "public",
            "registry_package", "status", "watch", "workflow_run"
        }

        if event_name not in known_events:
            # Log warning but don't fail - GitHub may add new event types
            # This is defensive but not blocking
            pass

        return event_name

    @staticmethod
    def sanitize_path_component(component: str, field_name: str = "path") -> str:
        """
        Sanitize a path component to prevent path traversal.

        Args:
            component: Path component to sanitize
            field_name: Name of field for error messages

        Returns:
            Sanitized path component

        Raises:
            ValidationError: If path contains dangerous patterns
        """
        if not component:
            raise ValidationError(f"{field_name} cannot be empty")

        # Check for path traversal patterns
        for pattern in InputValidator.PATH_TRAVERSAL_PATTERNS:
            if pattern in component:
                raise ValidationError(
                    f"{field_name} contains dangerous pattern: {pattern}"
                )

        # Check for absolute paths
        if component.startswith("/"):
            raise ValidationError(f"{field_name} cannot be an absolute path")

        # Check for Windows drive letters
        if re.match(r"^[a-zA-Z]:", component):
            raise ValidationError(f"{field_name} cannot contain drive letters")

        return component

    @staticmethod
    def validate_path_within_directory(path: Path, base_dir: Path) -> Path:
        """
        Validate that a path is within a base directory.

        Resolves both paths and ensures the target is within base_dir.

        Args:
            path: Path to validate
            base_dir: Base directory that path must be within

        Returns:
            Resolved path if valid

        Raises:
            ValidationError: If path is outside base_dir
        """
        try:
            # Resolve to absolute paths
            resolved_path = path.resolve()
            resolved_base = base_dir.resolve()

            # Check if path is relative to base
            try:
                resolved_path.relative_to(resolved_base)
            except ValueError:
                raise ValidationError(
                    f"Path {path} is outside allowed directory {base_dir}"
                )

            return resolved_path

        except (OSError, RuntimeError) as e:
            raise ValidationError(f"Failed to validate path: {e}")

    @staticmethod
    def sanitize_output_string(value: str, max_length: int = MAX_OUTPUT_STRING_LENGTH) -> str:
        """
        Sanitize a string for GitHub Action output.

        Removes control characters and limits length.

        Args:
            value: String to sanitize
            max_length: Maximum allowed length (default: MAX_OUTPUT_STRING_LENGTH)

        Returns:
            Sanitized string
        """
        if not value:
            return ""

        # Remove null bytes and other control characters (except newlines/tabs)
        sanitized = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", value)

        # Truncate if too long
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "...[truncated]"

        return sanitized

    @staticmethod
    def validate_integer(value: str, field_name: str = "value",
                        min_val: int | None = None,
                        max_val: int | None = None) -> int:
        """
        Validate and parse an integer value.

        Args:
            value: String value to parse
            field_name: Name of field for error messages
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Parsed integer

        Raises:
            ValidationError: If value is not a valid integer or out of range
        """
        try:
            int_val = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be an integer, got: {value}")

        if min_val is not None and int_val < min_val:
            raise ValidationError(
                f"{field_name} must be >= {min_val}, got: {int_val}"
            )

        if max_val is not None and int_val > max_val:
            raise ValidationError(
                f"{field_name} must be <= {max_val}, got: {int_val}"
            )

        return int_val
