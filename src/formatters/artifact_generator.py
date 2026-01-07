# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Artifact generator for metadata files.
Creates JSON and YAML artifact files for upload.
"""

import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from ..constants import ARTIFACT_SUFFIX_RANDOM_BYTES
from ..exceptions import ValidationError
from ..validators import InputValidator

if TYPE_CHECKING:
    from ..config import Config
    from ..models import CompleteMetadata


class ArtifactGenerator:
    """Generates artifact files from metadata."""

    def __init__(self, config: "Config"):
        """
        Initialize artifact generator.

        Args:
            config: Configuration object
        """
        self.config = config
        self.suffix = self._generate_suffix()

    def _generate_suffix(self) -> str:
        """
        Generate unique suffix for artifact naming.

        Uses datetime + secure random to avoid conflicts when action is called
        multiple times in parallel workflows.

        Format: {YYYYMMDD-HHMMSS}-{random_hex}
        Example: 20250107-143022-a1b2

        Returns:
            Unique suffix string (datetime-random format)
        """
        # Get current datetime in UTC
        now = datetime.now(timezone.utc)
        datetime_str = now.strftime("%Y%m%d-%H%M%S")

        # Generate secure random data for uniqueness
        random_hex = secrets.token_hex(ARTIFACT_SUFFIX_RANDOM_BYTES)

        # Combine for uniqueness: datetime ensures chronological ordering,
        # random_hex prevents collisions in parallel executions
        return f"{datetime_str}-{random_hex}"

    def generate(self, metadata: "CompleteMetadata") -> Path:
        """
        Generate artifact files from metadata.

        Creates a directory with JSON and/or YAML files based on configuration.

        Args:
            metadata: CompleteMetadata object to serialize

        Returns:
            Path to artifact directory

        Raises:
            ValidationError: If path validation fails
        """
        # Validate directory name components
        try:
            dir_name = f"repository-metadata-{self.suffix}"
            InputValidator.sanitize_path_component(dir_name, "artifact_dir")
        except ValidationError as e:
            raise ValidationError(f"Invalid artifact directory name: {e}")

        # Create artifact directory
        artifact_dir = self.config.RUNNER_TEMP / dir_name

        # Validate that artifact_dir is within RUNNER_TEMP
        try:
            validated_dir = InputValidator.validate_path_within_directory(
                artifact_dir, self.config.RUNNER_TEMP
            )
        except ValidationError as e:
            raise ValidationError(f"Artifact path validation failed: {e}")

        # Create the directory
        validated_dir.mkdir(parents=True, exist_ok=True)
        artifact_dir = validated_dir

        # Generate files based on requested formats
        formats = self.config.ARTIFACT_FORMATS

        if "json" in formats:
            self._write_json_files(artifact_dir, metadata)

        if "yaml" in formats:
            self._write_yaml_file(artifact_dir, metadata)

        return artifact_dir

    def _write_json_files(self, artifact_dir: Path, metadata: "CompleteMetadata"):
        """
        Write JSON artifact files.

        Creates both compact and pretty-printed versions.

        Args:
            artifact_dir: Directory to write files to
            metadata: Metadata to serialize
        """
        from .json_formatter import JsonFormatter

        formatter = JsonFormatter()
        include_comment = self.config.GERRIT_INCLUDE_COMMENT

        # Write compact JSON
        compact_json = formatter.format_compact(metadata, include_comment=include_comment)
        compact_file = artifact_dir / "repository-metadata.json"
        compact_file.write_text(compact_json, encoding="utf-8")

        # Write pretty JSON
        pretty_json = formatter.format_pretty(metadata, include_comment=include_comment)
        pretty_file = artifact_dir / "repository-metadata-pretty.json"
        pretty_file.write_text(pretty_json, encoding="utf-8")

    def _write_yaml_file(self, artifact_dir: Path, metadata: "CompleteMetadata"):
        """
        Write YAML artifact file.

        Args:
            artifact_dir: Directory to write files to
            metadata: Metadata to serialize
        """
        from .yaml_formatter import YamlFormatter

        formatter = YamlFormatter()
        include_comment = self.config.GERRIT_INCLUDE_COMMENT
        yaml_content = formatter.format(metadata, include_comment=include_comment)

        yaml_file = artifact_dir / "repository-metadata.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")
