# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Workflow run metadata extractor.
Extracts information about the workflow run that produced the metadata.
"""

from ..constants import DEFAULT_GITHUB_SERVER_URL
from ..models import WorkflowRunMetadata
from .base import BaseExtractor


class WorkflowRunExtractor(BaseExtractor):
    """Extracts workflow run (run ID, attempt, workflow, job) metadata."""

    def extract(self) -> WorkflowRunMetadata:
        """
        Extract workflow run metadata from environment.

        Returns:
            WorkflowRunMetadata object with workflow run information
        """
        self.debug("Extracting workflow run metadata")

        run_id = self._parse_integer("run ID", self.config.GITHUB_RUN_ID)
        run_attempt = self._parse_integer("run attempt", self.config.GITHUB_RUN_ATTEMPT)
        run_number = self._parse_integer("run number", self.config.GITHUB_RUN_NUMBER)
        run_url = self._build_run_url(run_id, run_attempt)

        metadata = WorkflowRunMetadata(
            run_id=run_id,
            run_attempt=run_attempt,
            run_number=run_number,
            workflow=self._text(self.config.GITHUB_WORKFLOW),
            workflow_ref=self._text(self.config.GITHUB_WORKFLOW_REF),
            job=self._text(self.config.GITHUB_JOB),
            run_url=run_url,
        )
        self.debug(f"Workflow run: {metadata.workflow} #{run_number} ({run_url})")
        return metadata

    def _parse_integer(self, label: str, value: int | str | None) -> int | None:
        """
        Parse an optional integer, warning when it is not numeric.

        Args:
            label: Human-readable field name for the warning
            value: Raw value from the configuration

        Returns:
            The integer, or None when unset or not numeric
        """
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (ValueError, TypeError) as e:
            self.warning(f"Failed to parse {label} '{value}': {e}")
            return None

    def _build_run_url(self, run_id: int | None, run_attempt: int | None) -> str:
        """
        Build the URL of the workflow run, naming the attempt after a re-run.

        Args:
            run_id: Workflow run ID
            run_attempt: Workflow run attempt

        Returns:
            The run URL, or an empty string when the run ID is unknown
        """
        repository = self._text(self.config.GITHUB_REPOSITORY)
        if run_id is None or not repository:
            return ""
        server_url = (
            self._text(self.config.GITHUB_SERVER_URL) or DEFAULT_GITHUB_SERVER_URL
        ).rstrip("/")
        url = f"{server_url}/{repository}/actions/runs/{run_id}"
        if run_attempt is not None and run_attempt > 1:
            url += f"/attempts/{run_attempt}"
        return url

    @staticmethod
    def _text(value: object) -> str:
        """Return a string value, or an empty string when unset."""
        return value if isinstance(value, str) else ""
