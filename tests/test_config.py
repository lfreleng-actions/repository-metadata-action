# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for configuration module.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

import src.config  # Needed to access module-level _config_instance
from src.config import Config, get_config
from src.exceptions import ConfigurationError


class TestConfigRequiredVars:
    """Tests for required environment variable loading."""

    @pytest.fixture(autouse=True)
    def reset_config(self):
        """Reset global config instance before each test."""
        src.config._config_instance = None
        yield
        src.config._config_instance = None

    @pytest.fixture
    def minimal_env(self, tmp_path):
        """Provide minimal required environment variables."""
        return {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "abc123def456789012345678901234567890abcd",
            "GITHUB_REPOSITORY_OWNER": "owner",
            "GITHUB_ACTOR": "testuser",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_OUTPUT": str(tmp_path / "output.txt"),
        }

    def test_load_all_required_vars(self, minimal_env, tmp_path):
        """Test loading all required environment variables."""
        # Create output file parent
        (tmp_path / "output.txt").touch()

        with patch.dict(os.environ, minimal_env, clear=True):
            config = Config()

            assert config.GITHUB_REPOSITORY == "owner/repo"
            assert config.GITHUB_SHA == "abc123def456789012345678901234567890abcd"
            assert config.GITHUB_REPOSITORY_OWNER == "owner"
            assert config.GITHUB_ACTOR == "testuser"
            assert config.GITHUB_EVENT_NAME == "push"
            assert Path(minimal_env["GITHUB_OUTPUT"]) == config.GITHUB_OUTPUT

    def test_missing_github_repository(self, minimal_env):
        """Test error when GITHUB_REPOSITORY is missing."""
        del minimal_env["GITHUB_REPOSITORY"]

        with patch.dict(os.environ, minimal_env, clear=True):
            with pytest.raises(ConfigurationError, match=r"GITHUB_REPOSITORY.*not set"):
                Config()

    def test_missing_github_sha(self, minimal_env):
        """Test error when GITHUB_SHA is missing."""
        del minimal_env["GITHUB_SHA"]

        with patch.dict(os.environ, minimal_env, clear=True):
            with pytest.raises(ConfigurationError, match=r"GITHUB_SHA.*not set"):
                Config()

    def test_missing_github_actor(self, minimal_env):
        """Test error when GITHUB_ACTOR is missing."""
        del minimal_env["GITHUB_ACTOR"]

        with patch.dict(os.environ, minimal_env, clear=True):
            with pytest.raises(ConfigurationError, match=r"GITHUB_ACTOR.*not set"):
                Config()

    def test_invalid_repository_format(self, minimal_env, tmp_path):
        """Test error for invalid repository format."""
        minimal_env["GITHUB_REPOSITORY"] = "invalid-no-slash"
        (tmp_path / "output.txt").touch()

        with patch.dict(os.environ, minimal_env, clear=True):
            with pytest.raises(ConfigurationError, match="Invalid GITHUB_REPOSITORY"):
                Config()

    def test_invalid_sha_format(self, minimal_env, tmp_path):
        """Test error for invalid SHA format."""
        minimal_env["GITHUB_SHA"] = "xyz123"  # Non-hex
        (tmp_path / "output.txt").touch()

        with patch.dict(os.environ, minimal_env, clear=True):
            with pytest.raises(ConfigurationError, match="Invalid GITHUB_SHA"):
                Config()

    def test_invalid_actor_format(self, minimal_env, tmp_path):
        """Test error for invalid actor format."""
        minimal_env["GITHUB_ACTOR"] = "user@name"  # Invalid character
        (tmp_path / "output.txt").touch()

        with patch.dict(os.environ, minimal_env, clear=True):
            with pytest.raises(ConfigurationError, match="Invalid GITHUB_ACTOR"):
                Config()

    def test_invalid_event_name(self, minimal_env, tmp_path):
        """Test error for invalid event name."""
        minimal_env["GITHUB_EVENT_NAME"] = "Push"  # Uppercase
        (tmp_path / "output.txt").touch()

        with patch.dict(os.environ, minimal_env, clear=True):
            with pytest.raises(ConfigurationError, match="Invalid GITHUB_EVENT_NAME"):
                Config()


class TestConfigOptionalVars:
    """Tests for optional environment variable loading."""

    @pytest.fixture(autouse=True)
    def reset_config(self):
        """Reset global config instance before each test."""
        src.config._config_instance = None
        yield
        src.config._config_instance = None

    @pytest.fixture
    def full_env(self, tmp_path):
        """Provide full environment with optional variables."""
        (tmp_path / "output.txt").touch()
        return {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "abc123def456789012345678901234567890abcd",
            "GITHUB_REPOSITORY_OWNER": "owner",
            "GITHUB_ACTOR": "testuser",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_OUTPUT": str(tmp_path / "output.txt"),
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_REF_NAME": "main",
            "GITHUB_REF_TYPE": "branch",
            "GITHUB_BASE_REF": "main",
            "GITHUB_HEAD_REF": "feature/test",
            "GITHUB_ACTOR_ID": "12345",
            "RUNNER_TEMP": str(tmp_path / "temp"),
            "REPO_VISIBILITY": "public",
            "PR_HEAD_REPO_FORK": "true",
            "DEFAULT_BRANCH": "main",
        }

    def test_load_optional_vars(self, full_env):
        """Test loading all optional environment variables."""
        with patch.dict(os.environ, full_env, clear=True):
            config = Config()

            assert config.GITHUB_REF == "refs/heads/main"
            assert config.GITHUB_REF_NAME == "main"
            assert config.GITHUB_REF_TYPE == "branch"
            assert config.GITHUB_BASE_REF == "main"
            assert config.GITHUB_HEAD_REF == "feature/test"
            assert config.GITHUB_ACTOR_ID == 12345
            assert config.REPO_VISIBILITY == "public"
            assert config.PR_HEAD_REPO_FORK is True
            assert config.DEFAULT_BRANCH == "main"

    def test_optional_vars_missing(self, full_env, tmp_path):
        """Test that missing optional vars don't cause errors."""
        # Remove all optional vars
        minimal_env = {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "abc123def456789012345678901234567890abcd",
            "GITHUB_REPOSITORY_OWNER": "owner",
            "GITHUB_ACTOR": "testuser",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_OUTPUT": str(tmp_path / "output.txt"),
        }
        (tmp_path / "output.txt").touch()

        with patch.dict(os.environ, minimal_env, clear=True):
            config = Config()

            assert config.GITHUB_REF is None
            assert config.GITHUB_REF_NAME is None
            assert config.GITHUB_REF_TYPE is None
            assert config.GITHUB_BASE_REF is None
            assert config.GITHUB_HEAD_REF is None
            assert config.GITHUB_ACTOR_ID is None

    def test_actor_id_parsing(self, full_env):
        """Test actor ID is parsed as integer."""
        full_env["GITHUB_ACTOR_ID"] = "99999"

        with patch.dict(os.environ, full_env, clear=True):
            config = Config()
            assert config.GITHUB_ACTOR_ID == 99999
            assert isinstance(config.GITHUB_ACTOR_ID, int)

    def test_invalid_actor_id(self, full_env):
        """Test invalid actor ID falls back gracefully."""
        full_env["GITHUB_ACTOR_ID"] = "not-a-number"

        with patch.dict(os.environ, full_env, clear=True):
            config = Config()
            # Should fall back to the string value
            assert config.GITHUB_ACTOR_ID == "not-a-number"

    def test_ref_type_validation(self, full_env):
        """Test GITHUB_REF_TYPE must be branch or tag."""
        full_env["GITHUB_REF_TYPE"] = "invalid"

        with patch.dict(os.environ, full_env, clear=True):
            with pytest.raises(ConfigurationError, match="Invalid GITHUB_REF_TYPE"):
                Config()

    def test_pr_head_repo_fork_parsing(self, full_env):
        """Test PR_HEAD_REPO_FORK boolean parsing."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("", False),
        ]

        for value, expected in test_cases:
            full_env["PR_HEAD_REPO_FORK"] = value

            with patch.dict(os.environ, full_env, clear=True):
                config = Config()
                assert config.PR_HEAD_REPO_FORK is expected


class TestConfigActionInputs:
    """Tests for action-specific input loading."""

    @pytest.fixture(autouse=True)
    def reset_config(self):
        """Reset global config instance before each test."""
        src.config._config_instance = None
        yield
        src.config._config_instance = None

    @pytest.fixture
    def base_env(self, tmp_path):
        """Base environment with action inputs."""
        (tmp_path / "output.txt").touch()
        return {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "abc123def456789012345678901234567890abcd",
            "GITHUB_REPOSITORY_OWNER": "owner",
            "GITHUB_ACTOR": "testuser",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_OUTPUT": str(tmp_path / "output.txt"),
        }

    def test_debug_mode_parsing(self, base_env):
        """Test debug mode boolean parsing."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("", False),
        ]

        for value, expected in test_cases:
            base_env["DEBUG_MODE"] = value

            with patch.dict(os.environ, base_env, clear=True):
                config = Config()
                assert config.DEBUG_MODE is expected

    def test_github_summary_parsing(self, base_env):
        """Test github summary boolean parsing."""
        base_env["GITHUB_SUMMARY"] = "true"

        with patch.dict(os.environ, base_env, clear=True):
            config = Config()
            assert config.GITHUB_SUMMARY is True

    def test_generate_summary_backward_compatibility(self, base_env):
        """Test that GENERATE_SUMMARY still works for backward compatibility."""
        base_env["GENERATE_SUMMARY"] = "true"

        with patch.dict(os.environ, base_env, clear=True):
            config = Config()
            assert config.GITHUB_SUMMARY is True

    def test_github_summary_takes_precedence(self, base_env):
        """Test that GITHUB_SUMMARY takes precedence over GENERATE_SUMMARY."""
        base_env["GITHUB_SUMMARY"] = "false"
        base_env["GENERATE_SUMMARY"] = "true"

        with patch.dict(os.environ, base_env, clear=True):
            config = Config()
            assert config.GITHUB_SUMMARY is False

    def test_change_detection_modes(self, base_env):
        """Test change detection mode validation."""
        valid_modes = ["auto", "git", "github_api"]

        for mode in valid_modes:
            base_env["CHANGE_DETECTION"] = mode

            with patch.dict(os.environ, base_env, clear=True):
                config = Config()
                assert mode == config.CHANGE_DETECTION

    def test_change_detection_invalid_mode(self, base_env):
        """Test invalid change detection mode falls back to auto."""
        base_env["CHANGE_DETECTION"] = "invalid"

        with patch.dict(os.environ, base_env, clear=True):
            config = Config()
            assert config.CHANGE_DETECTION == "auto"

    def test_git_fetch_depth_parsing(self, base_env):
        """Test git fetch depth integer parsing."""
        base_env["GIT_FETCH_DEPTH"] = "25"

        with patch.dict(os.environ, base_env, clear=True):
            config = Config()
            assert config.GIT_FETCH_DEPTH == 25

    def test_git_fetch_depth_invalid(self, base_env):
        """Test invalid git fetch depth falls back to default."""
        base_env["GIT_FETCH_DEPTH"] = "not-a-number"

        with patch.dict(os.environ, base_env, clear=True):
            config = Config()
            assert config.GIT_FETCH_DEPTH == 15

    def test_git_fetch_depth_bounds(self, base_env):
        """Test git fetch depth validates bounds."""
        base_env["GIT_FETCH_DEPTH"] = "99999"

        with patch.dict(os.environ, base_env, clear=True):
            config = Config()
            # Should be rejected and fall back to default
            assert config.GIT_FETCH_DEPTH == 15

    def test_artifact_formats_parsing(self, base_env):
        """Test artifact formats list parsing."""
        base_env["ARTIFACT_FORMATS"] = "json,yaml"

        with patch.dict(os.environ, base_env, clear=True):
            config = Config()
            assert config.ARTIFACT_FORMATS == ["json", "yaml"]

    def test_artifact_formats_single(self, base_env):
        """Test artifact formats with single format."""
        base_env["ARTIFACT_FORMATS"] = "json"

        with patch.dict(os.environ, base_env, clear=True):
            config = Config()
            assert config.ARTIFACT_FORMATS == ["json"]

    def test_artifact_formats_whitespace(self, base_env):
        """Test artifact formats strips whitespace."""
        base_env["ARTIFACT_FORMATS"] = " json , yaml "

        with patch.dict(os.environ, base_env, clear=True):
            config = Config()
            assert config.ARTIFACT_FORMATS == ["json", "yaml"]

    def test_gerrit_variables(self, base_env):
        """Test Gerrit environment variables."""
        base_env.update(
            {
                "GERRIT_BRANCH": "main",
                "GERRIT_CHANGE_ID": "I1234567890",
                "GERRIT_CHANGE_NUMBER": "12345",
            }
        )

        with patch.dict(os.environ, base_env, clear=True):
            config = Config()
            assert config.GERRIT_BRANCH == "main"
            assert config.GERRIT_CHANGE_ID == "I1234567890"
            assert config.GERRIT_CHANGE_NUMBER == "12345"


class TestConfigValidation:
    """Tests for configuration validation."""

    @pytest.fixture(autouse=True)
    def reset_config(self):
        """Reset global config instance before each test."""
        src.config._config_instance = None
        yield
        src.config._config_instance = None

    def test_validation_github_output_parent_exists(self, tmp_path):
        """Test validation checks GITHUB_OUTPUT parent directory exists."""
        env = {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "abc123def456789012345678901234567890abcd",
            "GITHUB_REPOSITORY_OWNER": "owner",
            "GITHUB_ACTOR": "testuser",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_OUTPUT": str(tmp_path / "output.txt"),
        }

        # Parent exists
        with patch.dict(os.environ, env, clear=True):
            config = Config()
            assert config.GITHUB_OUTPUT.parent == tmp_path

    def test_validation_github_output_parent_missing(self, tmp_path):
        """Test validation fails if GITHUB_OUTPUT parent doesn't exist."""
        env = {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "abc123def456789012345678901234567890abcd",
            "GITHUB_REPOSITORY_OWNER": "owner",
            "GITHUB_ACTOR": "testuser",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_OUTPUT": str(tmp_path / "nonexistent" / "output.txt"),
        }

        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ConfigurationError, match="parent directory does not exist"):
                Config()


class TestConfigGlobalInstance:
    """Tests for global config instance management."""

    @pytest.fixture(autouse=True)
    def reset_config(self):
        """Reset global config instance before each test."""
        src.config._config_instance = None
        yield
        src.config._config_instance = None

    def test_get_config_creates_instance(self, tmp_path):
        """Test get_config creates instance on first call."""
        env = {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "abc123def456789012345678901234567890abcd",
            "GITHUB_REPOSITORY_OWNER": "owner",
            "GITHUB_ACTOR": "testuser",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_OUTPUT": str(tmp_path / "output.txt"),
        }
        (tmp_path / "output.txt").touch()

        with patch.dict(os.environ, env, clear=True):
            config = get_config()
            assert config is not None
            assert isinstance(config, Config)

    def test_get_config_returns_same_instance(self, tmp_path):
        """Test get_config returns same instance on subsequent calls."""
        env = {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "abc123def456789012345678901234567890abcd",
            "GITHUB_REPOSITORY_OWNER": "owner",
            "GITHUB_ACTOR": "testuser",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_OUTPUT": str(tmp_path / "output.txt"),
        }
        (tmp_path / "output.txt").touch()

        with patch.dict(os.environ, env, clear=True):
            config1 = get_config()
            config2 = get_config()
            assert config1 is config2

    def test_config_singleton_pattern(self, tmp_path):
        """Test Config uses singleton pattern."""
        env = {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SHA": "abc123def456789012345678901234567890abcd",
            "GITHUB_REPOSITORY_OWNER": "owner",
            "GITHUB_ACTOR": "testuser",
            "GITHUB_EVENT_NAME": "push",
            "GITHUB_OUTPUT": str(tmp_path / "output.txt"),
        }
        (tmp_path / "output.txt").touch()

        with patch.dict(os.environ, env, clear=True):
            # First call creates instance
            config1 = get_config()

            # Second call returns same instance
            config2 = get_config()

            assert config1 is config2
