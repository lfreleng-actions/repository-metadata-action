# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for ActorExtractor.
"""

from unittest.mock import Mock

import pytest

from src.extractors.actor import ActorExtractor
from src.models import ActorMetadata


@pytest.fixture
def mock_config():
    """Create a mock config object."""
    config = Mock()
    config.GITHUB_ACTOR = "testuser"
    config.GITHUB_ACTOR_ID = "123456"
    config.GITHUB_RUN_ID = "12345"
    config.GITHUB_WORKFLOW = "CI"
    config.DEBUG_MODE = False
    return config


class TestActorExtractor:
    """Test suite for ActorExtractor."""

    def test_extract_with_actor_name_and_id(self, mock_config):
        """Test extraction with both actor name and ID."""
        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert isinstance(result, ActorMetadata)
        assert result.name == "testuser"
        assert result.id == 123456

    def test_extract_with_actor_name_only(self, mock_config):
        """Test extraction with only actor name (no ID)."""
        mock_config.GITHUB_ACTOR_ID = None

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "testuser"
        assert result.id is None

    def test_extract_with_empty_actor_id(self, mock_config):
        """Test extraction with empty actor ID string."""
        mock_config.GITHUB_ACTOR_ID = ""

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "testuser"
        assert result.id is None

    def test_extract_with_invalid_actor_id_non_numeric(self, mock_config):
        """Test extraction with invalid (non-numeric) actor ID."""
        mock_config.GITHUB_ACTOR_ID = "not-a-number"

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "testuser"
        assert result.id is None

    def test_extract_with_invalid_actor_id_float(self, mock_config):
        """Test extraction with float actor ID (should fail)."""
        mock_config.GITHUB_ACTOR_ID = "123.456"

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "testuser"
        assert result.id is None

    def test_extract_with_actor_id_as_integer(self, mock_config):
        """Test extraction when actor ID is already an integer."""
        mock_config.GITHUB_ACTOR_ID = 789012

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "testuser"
        assert result.id == 789012

    def test_extract_with_large_actor_id(self, mock_config):
        """Test extraction with large actor ID."""
        mock_config.GITHUB_ACTOR_ID = "999999999999"

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "testuser"
        assert result.id == 999999999999

    def test_extract_with_zero_actor_id(self, mock_config):
        """Test extraction with zero actor ID."""
        mock_config.GITHUB_ACTOR_ID = "0"

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "testuser"
        assert result.id == 0

    def test_extract_with_negative_actor_id(self, mock_config):
        """Test extraction with negative actor ID (should work but unusual)."""
        mock_config.GITHUB_ACTOR_ID = "-123"

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "testuser"
        assert result.id == -123

    def test_extract_with_special_characters_in_name(self, mock_config):
        """Test extraction with special characters in actor name."""
        mock_config.GITHUB_ACTOR = "user-with-dashes"

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "user-with-dashes"
        assert result.id == 123456

    def test_extract_with_bot_actor(self, mock_config):
        """Test extraction with bot actor name."""
        mock_config.GITHUB_ACTOR = "dependabot[bot]"
        mock_config.GITHUB_ACTOR_ID = "49699333"

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "dependabot[bot]"
        assert result.id == 49699333

    def test_extract_with_github_actions_actor(self, mock_config):
        """Test extraction with github-actions actor."""
        mock_config.GITHUB_ACTOR = "github-actions[bot]"
        mock_config.GITHUB_ACTOR_ID = "41898282"

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "github-actions[bot]"
        assert result.id == 41898282

    def test_extract_with_long_actor_name(self, mock_config):
        """Test extraction with very long actor name."""
        long_name = "a" * 100
        mock_config.GITHUB_ACTOR = long_name

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == long_name
        assert result.id == 123456

    def test_extract_with_unicode_actor_name(self, mock_config):
        """Test extraction with unicode characters in actor name."""
        mock_config.GITHUB_ACTOR = "user-名前-👤"

        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        assert result.name == "user-名前-👤"
        assert result.id == 123456

    def test_logging_output(self, mock_config, caplog):
        """Test that appropriate logging messages are generated."""
        import logging

        caplog.set_level(logging.INFO)

        mock_config.DEBUG_MODE = True

        extractor = ActorExtractor(mock_config)
        _ = extractor.extract()

        assert "Actor: testuser" in caplog.text

    def test_logging_warning_on_invalid_id(self, mock_config, caplog):
        """Test warning is logged when actor ID parsing fails."""
        import logging

        caplog.set_level(logging.WARNING)

        mock_config.GITHUB_ACTOR_ID = "invalid"
        mock_config.DEBUG_MODE = True

        extractor = ActorExtractor(mock_config)
        _ = extractor.extract()

        assert "Failed to parse actor ID" in caplog.text
        assert "'invalid'" in caplog.text

    def test_logging_no_actor_id_warning_when_none(self, mock_config, caplog):
        """Test no warning is logged when actor ID is None."""
        import logging

        caplog.set_level(logging.WARNING)

        mock_config.GITHUB_ACTOR_ID = None
        mock_config.DEBUG_MODE = True

        extractor = ActorExtractor(mock_config)
        _ = extractor.extract()

        # Should not contain warning about parsing failure
        assert "Failed to parse actor ID" not in caplog.text

    def test_extract_preserves_actor_name_exactly(self, mock_config):
        """Test that actor name is preserved exactly as provided."""
        test_cases = [
            "CamelCase",
            "snake_case",
            "kebab-case",
            "MixedCase_With-Everything123",
            "user.with.dots",
        ]

        for test_name in test_cases:
            mock_config.GITHUB_ACTOR = test_name
            extractor = ActorExtractor(mock_config)
            result = extractor.extract()
            assert result.name == test_name

    def test_actor_metadata_model_compliance(self, mock_config):
        """Test that extracted data complies with ActorMetadata model."""
        extractor = ActorExtractor(mock_config)
        result = extractor.extract()

        # Verify model fields exist
        assert hasattr(result, "name")
        assert hasattr(result, "id")

        # Verify types
        assert isinstance(result.name, str)
        assert isinstance(result.id, int) or result.id is None
