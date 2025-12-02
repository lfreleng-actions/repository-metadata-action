# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for input validation and sanitization utilities.
"""

import tempfile
from pathlib import Path

import pytest

from src.exceptions import ValidationError
from src.validators import InputValidator


class TestSHAValidation:
    """Tests for SHA validation."""

    def test_valid_sha_40_chars(self):
        """Test valid 40-character SHA-1."""
        sha = "abc123def456789012345678901234567890abcd"
        result = InputValidator.validate_sha(sha)
        assert result == sha

    def test_valid_sha_7_chars(self):
        """Test valid 7-character short SHA."""
        sha = "abc123d"
        result = InputValidator.validate_sha(sha)
        assert result == sha

    def test_valid_sha_64_chars(self):
        """Test valid 64-character SHA-256."""
        sha = "a" * 64
        result = InputValidator.validate_sha(sha)
        assert result == sha

    def test_valid_sha_mixed_case(self):
        """Test SHA with mixed case."""
        sha = "AbC123DeF456"
        result = InputValidator.validate_sha(sha)
        assert result == sha

    def test_invalid_sha_empty(self):
        """Test empty SHA raises error."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            InputValidator.validate_sha("")

    def test_invalid_sha_non_hex(self):
        """Test non-hexadecimal characters."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_sha("xyz123")

    def test_invalid_sha_special_chars(self):
        """Test SHA with special characters."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_sha("abc123-def456")

    def test_invalid_sha_too_short(self):
        """Test SHA that's too short."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_sha("abc12")

    def test_invalid_sha_spaces(self):
        """Test SHA with spaces."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_sha("abc123 def456")


class TestRepositoryNameValidation:
    """Tests for repository name validation."""

    def test_valid_repo_name(self):
        """Test valid repository name."""
        repo = "owner/repo"
        result = InputValidator.validate_repository_name(repo)
        assert result == repo

    def test_valid_repo_with_dash(self):
        """Test repository name with dashes."""
        repo = "my-org/my-repo"
        result = InputValidator.validate_repository_name(repo)
        assert result == repo

    def test_valid_repo_with_underscore(self):
        """Test repository name with underscores."""
        repo = "my_org/my_repo"
        result = InputValidator.validate_repository_name(repo)
        assert result == repo

    def test_valid_repo_with_dot(self):
        """Test repository name with dots."""
        repo = "my.org/my.repo"
        result = InputValidator.validate_repository_name(repo)
        assert result == repo

    def test_valid_repo_with_numbers(self):
        """Test repository name with numbers."""
        repo = "org123/repo456"
        result = InputValidator.validate_repository_name(repo)
        assert result == repo

    def test_invalid_repo_empty(self):
        """Test empty repository name."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            InputValidator.validate_repository_name("")

    def test_invalid_repo_no_slash(self):
        """Test repository name without slash."""
        with pytest.raises(ValidationError, match="owner/repo"):
            InputValidator.validate_repository_name("justarepo")

    def test_invalid_repo_multiple_slashes(self):
        """Test repository name with multiple slashes."""
        with pytest.raises(ValidationError, match="owner/repo"):
            InputValidator.validate_repository_name("owner/sub/repo")

    def test_invalid_repo_owner_too_long(self):
        """Test repository with owner name too long."""
        long_owner = "a" * 40
        with pytest.raises(ValidationError, match="Owner name too long"):
            InputValidator.validate_repository_name(f"{long_owner}/repo")

    def test_invalid_repo_name_too_long(self):
        """Test repository with repo name too long."""
        long_repo = "a" * 101
        with pytest.raises(ValidationError, match="Repository name too long"):
            InputValidator.validate_repository_name(f"owner/{long_repo}")

    def test_invalid_repo_special_chars(self):
        """Test repository with invalid special characters."""
        with pytest.raises(ValidationError, match="owner/repo"):
            InputValidator.validate_repository_name("owner$/repo!")


class TestRefNameValidation:
    """Tests for reference name validation."""

    def test_valid_branch_name(self):
        """Test valid branch name."""
        ref = "main"
        result = InputValidator.validate_ref_name(ref)
        assert result == ref

    def test_valid_ref_with_slash(self):
        """Test ref with slashes (feature/branch)."""
        ref = "feature/new-feature"
        result = InputValidator.validate_ref_name(ref)
        assert result == ref

    def test_valid_ref_with_numbers(self):
        """Test ref with numbers."""
        ref = "release-1.2.3"
        result = InputValidator.validate_ref_name(ref)
        assert result == ref

    def test_valid_tag_name(self):
        """Test valid tag name."""
        ref = "v1.0.0"
        result = InputValidator.validate_ref_name(ref)
        assert result == ref

    def test_valid_refs_path(self):
        """Test refs/heads/branch format."""
        ref = "refs/heads/main"
        result = InputValidator.validate_ref_name(ref)
        assert result == ref

    def test_invalid_ref_empty(self):
        """Test empty ref name."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            InputValidator.validate_ref_name("")

    def test_invalid_ref_starts_with_dash(self):
        """Test ref starting with dash."""
        with pytest.raises(ValidationError, match="cannot start with dash"):
            InputValidator.validate_ref_name("-branch")

    def test_invalid_ref_double_slash(self):
        """Test ref with consecutive slashes."""
        with pytest.raises(ValidationError, match="consecutive slashes"):
            InputValidator.validate_ref_name("feature//branch")

    def test_invalid_ref_special_chars(self):
        """Test ref with invalid characters."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_ref_name("branch@name")

    def test_invalid_ref_too_long(self):
        """Test ref name that's too long."""
        long_ref = "a" * 257
        with pytest.raises(ValidationError, match="too long"):
            InputValidator.validate_ref_name(long_ref)

    def test_invalid_ref_spaces(self):
        """Test ref with spaces."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_ref_name("feature branch")


class TestActorNameValidation:
    """Tests for actor name validation."""

    def test_valid_actor(self):
        """Test valid actor name."""
        actor = "username"
        result = InputValidator.validate_actor_name(actor)
        assert result == actor

    def test_valid_actor_with_dash(self):
        """Test actor with dashes."""
        actor = "user-name"
        result = InputValidator.validate_actor_name(actor)
        assert result == actor

    def test_valid_actor_with_numbers(self):
        """Test actor with numbers."""
        actor = "user123"
        result = InputValidator.validate_actor_name(actor)
        assert result == actor

    def test_valid_actor_max_length(self):
        """Test actor at max length (39 chars)."""
        actor = "a" * 39
        result = InputValidator.validate_actor_name(actor)
        assert result == actor

    def test_invalid_actor_empty(self):
        """Test empty actor name."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            InputValidator.validate_actor_name("")

    def test_invalid_actor_too_long(self):
        """Test actor name too long."""
        actor = "a" * 40
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_actor_name(actor)

    def test_invalid_actor_starts_with_dash(self):
        """Test actor starting with dash."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_actor_name("-username")

    def test_invalid_actor_underscore(self):
        """Test actor with underscore (not allowed by GitHub)."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_actor_name("user_name")

    def test_invalid_actor_special_chars(self):
        """Test actor with special characters."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_actor_name("user@name")


class TestEventNameValidation:
    """Tests for event name validation."""

    def test_valid_event_push(self):
        """Test valid push event."""
        event = "push"
        result = InputValidator.validate_event_name(event)
        assert result == event

    def test_valid_event_pull_request(self):
        """Test valid pull_request event."""
        event = "pull_request"
        result = InputValidator.validate_event_name(event)
        assert result == event

    def test_valid_event_workflow_dispatch(self):
        """Test valid workflow_dispatch event."""
        event = "workflow_dispatch"
        result = InputValidator.validate_event_name(event)
        assert result == event

    def test_invalid_event_empty(self):
        """Test empty event name."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            InputValidator.validate_event_name("")

    def test_invalid_event_uppercase(self):
        """Test event with uppercase."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_event_name("Push")

    def test_invalid_event_dash(self):
        """Test event with dash."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_event_name("pull-request")

    def test_invalid_event_special_chars(self):
        """Test event with special characters."""
        with pytest.raises(ValidationError, match="invalid characters"):
            InputValidator.validate_event_name("push!")


class TestPathSanitization:
    """Tests for path sanitization."""

    def test_valid_path_component(self):
        """Test valid path component."""
        path = "my-directory"
        result = InputValidator.sanitize_path_component(path)
        assert result == path

    def test_invalid_path_parent_traversal(self):
        """Test path with parent directory traversal."""
        with pytest.raises(ValidationError, match="dangerous pattern"):
            InputValidator.sanitize_path_component("../etc/passwd")

    def test_invalid_path_home_directory(self):
        """Test path with home directory."""
        with pytest.raises(ValidationError, match="dangerous pattern"):
            InputValidator.sanitize_path_component("~/file")

    def test_invalid_path_variable(self):
        """Test path with variable expansion."""
        with pytest.raises(ValidationError, match="dangerous pattern"):
            InputValidator.sanitize_path_component("$HOME/file")

    def test_invalid_path_command_substitution(self):
        """Test path with command substitution."""
        with pytest.raises(ValidationError, match="dangerous pattern"):
            InputValidator.sanitize_path_component("`whoami`")

    def test_invalid_path_null_byte(self):
        """Test path with null byte."""
        with pytest.raises(ValidationError, match="dangerous pattern"):
            InputValidator.sanitize_path_component("file\x00name")

    def test_invalid_path_newline(self):
        """Test path with newline."""
        with pytest.raises(ValidationError, match="dangerous pattern"):
            InputValidator.sanitize_path_component("file\nname")

    def test_invalid_path_absolute(self):
        """Test absolute path."""
        with pytest.raises(ValidationError, match="absolute path"):
            InputValidator.sanitize_path_component("/etc/passwd")

    def test_invalid_path_drive_letter(self):
        """Test Windows drive letter."""
        with pytest.raises(ValidationError, match="drive letters"):
            InputValidator.sanitize_path_component("C:\\Windows")

    def test_invalid_path_empty(self):
        """Test empty path."""
        with pytest.raises(ValidationError, match="cannot be empty"):
            InputValidator.sanitize_path_component("")


class TestPathWithinDirectory:
    """Tests for path within directory validation."""

    def test_valid_path_within_directory(self):
        """Test path that is within base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base / "subdir" / "file.txt"

            result = InputValidator.validate_path_within_directory(target, base)
            assert str(result).startswith(str(base.resolve()))

    def test_invalid_path_outside_directory(self):
        """Test path that is outside base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "subdir"
            base.mkdir()
            target = Path(tmpdir) / "outside.txt"

            with pytest.raises(ValidationError, match="outside allowed directory"):
                InputValidator.validate_path_within_directory(target, base)

    def test_invalid_path_traversal_attempt(self):
        """Test path traversal attempt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir) / "subdir"
            base.mkdir()
            # This will resolve to parent directory
            target = base / ".." / "outside.txt"

            with pytest.raises(ValidationError, match="outside allowed directory"):
                InputValidator.validate_path_within_directory(target, base)

    def test_valid_path_same_as_base(self):
        """Test path that is the same as base directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            target = base

            result = InputValidator.validate_path_within_directory(target, base)
            assert result == base.resolve()


class TestOutputStringSanitization:
    """Tests for output string sanitization."""

    def test_valid_string(self):
        """Test valid string passes through."""
        text = "Hello, World!"
        result = InputValidator.sanitize_output_string(text)
        assert result == text

    def test_string_with_newlines(self):
        """Test string with newlines is preserved."""
        text = "Line 1\nLine 2\nLine 3"
        result = InputValidator.sanitize_output_string(text)
        assert result == text

    def test_string_with_tabs(self):
        """Test string with tabs is preserved."""
        text = "Column1\tColumn2\tColumn3"
        result = InputValidator.sanitize_output_string(text)
        assert result == text

    def test_removes_null_bytes(self):
        """Test null bytes are removed."""
        text = "Hello\x00World"
        result = InputValidator.sanitize_output_string(text)
        assert result == "HelloWorld"
        assert "\x00" not in result

    def test_removes_control_characters(self):
        """Test control characters are removed."""
        text = "Hello\x01\x02\x03World"
        result = InputValidator.sanitize_output_string(text)
        assert result == "HelloWorld"

    def test_truncates_long_string(self):
        """Test long strings are truncated."""
        text = "a" * 20000
        result = InputValidator.sanitize_output_string(text, max_length=100)
        assert len(result) <= 120  # 100 + "[truncated]"
        assert "[truncated]" in result

    def test_empty_string(self):
        """Test empty string."""
        result = InputValidator.sanitize_output_string("")
        assert result == ""

    def test_unicode_characters(self):
        """Test unicode characters are preserved."""
        text = "Hello 世界 🌍"
        result = InputValidator.sanitize_output_string(text)
        assert result == text


class TestIntegerValidation:
    """Tests for integer validation."""

    def test_valid_integer(self):
        """Test valid integer string."""
        result = InputValidator.validate_integer("42")
        assert result == 42

    def test_valid_negative_integer(self):
        """Test valid negative integer."""
        result = InputValidator.validate_integer("-10")
        assert result == -10

    def test_valid_zero(self):
        """Test zero."""
        result = InputValidator.validate_integer("0")
        assert result == 0

    def test_integer_with_min_value(self):
        """Test integer with minimum value check."""
        result = InputValidator.validate_integer("10", min_val=5)
        assert result == 10

    def test_integer_with_max_value(self):
        """Test integer with maximum value check."""
        result = InputValidator.validate_integer("10", max_val=20)
        assert result == 10

    def test_integer_at_min_boundary(self):
        """Test integer at minimum boundary."""
        result = InputValidator.validate_integer("5", min_val=5)
        assert result == 5

    def test_integer_at_max_boundary(self):
        """Test integer at maximum boundary."""
        result = InputValidator.validate_integer("10", max_val=10)
        assert result == 10

    def test_invalid_integer_non_numeric(self):
        """Test non-numeric string."""
        with pytest.raises(ValidationError, match="must be an integer"):
            InputValidator.validate_integer("abc")

    def test_invalid_integer_float(self):
        """Test float string."""
        with pytest.raises(ValidationError, match="must be an integer"):
            InputValidator.validate_integer("3.14")

    def test_invalid_integer_below_min(self):
        """Test integer below minimum."""
        with pytest.raises(ValidationError, match="must be >= 10"):
            InputValidator.validate_integer("5", min_val=10)

    def test_invalid_integer_above_max(self):
        """Test integer above maximum."""
        with pytest.raises(ValidationError, match="must be <= 10"):
            InputValidator.validate_integer("15", max_val=10)

    def test_invalid_integer_empty(self):
        """Test empty string."""
        with pytest.raises(ValidationError, match="must be an integer"):
            InputValidator.validate_integer("")
