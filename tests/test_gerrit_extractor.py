# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for GerritExtractor.
"""

import json
import logging
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.extractors.gerrit import GerritExtractor
from src.models import GerritMetadata


@pytest.fixture
def mock_config(tmp_path):
    """Create a mock config object with no Gerrit environment data."""
    config = Mock()
    config.GITHUB_EVENT_NAME = "workflow_dispatch"
    config.GITHUB_EVENT_PATH = tmp_path / "event.json"
    config.GITHUB_SHA = "0123456789abcdef0123456789abcdef01234567"
    config.GITHUB_REF_NAME = "master"
    config.DEBUG_MODE = False
    config.GERRIT_INCLUDE_COMMENT = False
    config.GERRIT_BRANCH = None
    config.GERRIT_CHANGE_ID = None
    config.GERRIT_CHANGE_NUMBER = None
    config.GERRIT_CHANGE_URL = None
    config.GERRIT_EVENT_TYPE = None
    config.GERRIT_PATCHSET_NUMBER = None
    config.GERRIT_PATCHSET_REVISION = None
    config.GERRIT_PROJECT = None
    config.GERRIT_REFSPEC = None
    config.GERRIT_COMMENT = None
    return config


def write_event(config, payload):
    """Write a JSON event payload to the mock event path."""
    Path(config.GITHUB_EVENT_PATH).write_text(json.dumps(payload))


class TestGerritExtractor:
    """Test suite for GerritExtractor."""

    def test_extract_null_inputs_no_error(self, mock_config, caplog):
        """Dispatch payload with "inputs": null must not log an error."""
        write_event(mock_config, {"inputs": None})

        extractor = GerritExtractor(mock_config)
        with caplog.at_level(logging.ERROR):
            result = extractor.extract()

        assert isinstance(result, GerritMetadata)
        assert result.source == "none"
        assert not caplog.records

    def test_extract_missing_inputs_key(self, mock_config):
        """Dispatch payload without an inputs key returns empty metadata."""
        write_event(mock_config, {})

        extractor = GerritExtractor(mock_config)
        result = extractor.extract()

        assert isinstance(result, GerritMetadata)
        assert result.source == "none"

    def test_extract_gerrit_json_input(self, mock_config):
        """Consolidated gerrit_json input is parsed into metadata."""
        gerrit = {
            "branch": "master",
            "change_id": "I" + "a" * 40,
            "change_number": "146351",
            "change_url": "https://gerrit.onap.org/r/c/policy/opa-pdp/+/146351",
            "event_type": "patchset-created",
            "patchset_number": "2",
            "patchset_revision": "0123456789abcdef0123456789abcdef01234567",
            "project": "policy/opa-pdp",
            "refspec": "refs/changes/51/146351/2",
        }
        write_event(mock_config, {"inputs": {"gerrit_json": json.dumps(gerrit)}})

        extractor = GerritExtractor(mock_config)
        result = extractor.extract()

        assert result is not None
        assert result.source == "workflow_dispatch (gerrit_json)"
        assert result.change_number == "146351"
        assert result.project == "policy/opa-pdp"

    def test_extract_individual_gerrit_inputs(self, mock_config):
        """Individual GERRIT_* dispatch inputs are extracted."""
        write_event(
            mock_config,
            {
                "inputs": {
                    "GERRIT_BRANCH": "master",
                    "GERRIT_CHANGE_NUMBER": "146351",
                    "GERRIT_PROJECT": "policy/opa-pdp",
                }
            },
        )

        extractor = GerritExtractor(mock_config)
        result = extractor.extract()

        assert result is not None
        assert result.source == "workflow_dispatch (gerrit_to_platform inputs)"
        assert result.branch == "master"
        assert result.change_number == "146351"
