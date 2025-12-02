# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Main entry point for the repository metadata action.
Orchestrates metadata extraction, formatting, and output generation.
"""

import logging
import secrets
import sys
from pathlib import Path
from typing import Literal

from .config import get_config
from .constants import GITHUB_OUTPUT_DELIMITER_RANDOM_BYTES
from .exceptions import MetadataExtractionError
from .extractors import (
    ActorExtractor,
    CacheExtractor,
    ChangedFilesExtractor,
    ChangedFilesLastCommitExtractor,
    CommitExtractor,
    EventExtractor,
    GerritExtractor,
    PullRequestExtractor,
    RefExtractor,
    RepositoryExtractor,
)
from .formatters import ArtifactGenerator, JsonFormatter, MarkdownFormatter, YamlFormatter
from .git_operations import GitOperations
from .github_api import GitHubAPI
from .models import CompleteMetadata


def setup_logging() -> logging.Logger:
    """
    Configure logging based on debug mode.

    Returns:
        Configured logger instance
    """
    config = get_config()
    level = logging.DEBUG if config.DEBUG_MODE else logging.INFO

    # Configure logging format
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    return logging.getLogger("repository-metadata")


def write_github_output(outputs: dict[str, str], output_file: Path) -> None:
    """
    Write outputs to GITHUB_OUTPUT file.

    Handles both single-line and multi-line values using proper delimiters.

    Args:
        outputs: Dictionary of output name -> value pairs
        output_file: Path to GITHUB_OUTPUT file
    """
    with open(output_file, "a", encoding="utf-8") as f:
        for name, value in outputs.items():
            value_str = str(value)

            if "\n" in value_str:
                # Multi-line value - use delimiter format
                delimiter = f"EOF_{secrets.token_hex(GITHUB_OUTPUT_DELIMITER_RANDOM_BYTES)}"
                f.write(f"{name}<<{delimiter}\n{value_str}\n{delimiter}\n")
            else:
                # Single-line value
                f.write(f"{name}={value_str}\n")


def write_step_summary(content: str, summary_file: Path | None) -> None:
    """
    Write content to GitHub Step Summary.

    Args:
        content: Markdown content to write
        summary_file: Path to GITHUB_STEP_SUMMARY file (None if not available)
    """
    if not summary_file:
        return

    with open(summary_file, "a", encoding="utf-8") as f:
        f.write(content)


def print_summary(metadata: CompleteMetadata) -> None:
    """
    Print a brief summary to console.

    Args:
        metadata: Complete metadata object
    """
    print("\n" + "="*60)
    print("Repository Metadata Extraction Complete")
    print("="*60)
    print(f"Repository: {metadata.repository.full_name}")
    print(f"Event: {metadata.event.name}")
    print(f"Commit: {metadata.commit.sha_short}")
    print(f"Actor: {metadata.actor.name}")

    if metadata.ref.branch_name:
        print(f"Branch: {metadata.ref.branch_name}")
    if metadata.ref.tag_name:
        print(f"Tag: {metadata.ref.tag_name}")
    if metadata.pull_request.number:
        print(f"Pull Request: #{metadata.pull_request.number}")
    if metadata.changed_files.count > 0:
        print(f"Changed Files: {metadata.changed_files.count}")
    # Always print Gerrit info since gerrit_environment is always present
    if metadata.gerrit_environment.change_id:
        print(f"Gerrit Change-ID: {metadata.gerrit_environment.change_id}")
    elif metadata.gerrit_environment.source != "none":
        print(f"Gerrit Change-ID: N/A")

    print("="*60 + "\n")


def main() -> int:
    """
    Main execution function.

    Orchestrates the entire metadata extraction process:
    1. Load configuration
    2. Extract metadata from all sources
    3. Format outputs (JSON, YAML, Markdown)
    4. Write GitHub Action outputs
    5. Generate optional summary and artifacts
    """
    logger = setup_logging()
    logger.info("Starting repository metadata extraction")

    try:
        # Load configuration
        config = get_config()

        # Initialize GitHub API client with context manager for proper cleanup
        github_api: GitHubAPI | None = None
        if config.GITHUB_TOKEN:
            try:
                github_api = GitHubAPI(config.GITHUB_TOKEN, logger=logger)
                logger.debug("GitHub API client initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub API: {e}")
                github_api = None

        # Use context manager if github_api was initialized
        github_api_context = github_api if github_api else _NullContextManager()

        with github_api_context:
            git_ops = GitOperations(logger=logger)
            if git_ops.has_git_repo():
                logger.debug("Git repository detected")
            else:
                logger.debug("No git repository available")

            # Extract all metadata components
            logger.info("Extracting repository metadata...")
            repository = RepositoryExtractor(config, github_api, logger=logger).extract()

            logger.info("Extracting event metadata...")
            event = EventExtractor(config, logger=logger).extract()

            logger.info("Extracting ref metadata...")
            ref = RefExtractor(config, github_api, logger=logger).extract()

            logger.info("Extracting commit metadata...")
            commit = CommitExtractor(config, git_ops, logger=logger).extract()

            logger.info("Extracting pull request metadata...")
            pull_request = PullRequestExtractor(config, github_api, logger=logger).extract()

            logger.info("Extracting actor metadata...")
            actor = ActorExtractor(config, logger=logger).extract()

            logger.info("Generating cache keys...")
            cache = CacheExtractor(config, logger=logger).extract()

            logger.info("Detecting changed files...")
            changed_files = ChangedFilesExtractor(config, github_api, git_ops, logger=logger).extract()

            logger.info("Detecting changed files in last commit...")
            changed_files_last_commit = ChangedFilesLastCommitExtractor(config, git_ops, logger=logger).extract()

            logger.info("Checking for Gerrit metadata...")
            gerrit = GerritExtractor(config, git_ops, logger=logger).extract()

            # Combine into complete metadata
            metadata = CompleteMetadata(
                repository=repository,
                event=event,
                ref=ref,
                commit=commit,
                pull_request=pull_request,
                actor=actor,
                cache=cache,
                changed_files=changed_files,
                changed_files_last_commit=changed_files_last_commit,
                gerrit_environment=gerrit
            )

            logger.info("Metadata extraction complete")

            # Generate outputs
            logger.info("Generating GitHub Action outputs...")
            outputs = metadata.to_action_outputs(include_comment=config.GERRIT_INCLUDE_COMMENT)

            # Add formatted JSON and YAML outputs
            json_formatter = JsonFormatter()
            yaml_formatter = YamlFormatter()

            outputs["metadata_json"] = json_formatter.format_compact(metadata, include_comment=config.GERRIT_INCLUDE_COMMENT)
            outputs["metadata_yaml"] = yaml_formatter.format(metadata, include_comment=config.GERRIT_INCLUDE_COMMENT)

            # Write outputs to GITHUB_OUTPUT
            write_github_output(outputs, config.GITHUB_OUTPUT)
            logger.info(f"Outputs written to {config.GITHUB_OUTPUT}")

            # Generate optional GitHub Step Summaries
            # GitHub and Gerrit summaries can be enabled independently
            if config.GITHUB_STEP_SUMMARY:
                markdown_formatter = MarkdownFormatter()

                # Generate GitHub summary
                if config.GITHUB_SUMMARY:
                    logger.info("Generating GitHub execution environment summary...")
                    github_summary = markdown_formatter.format(
                        metadata,
                        include_gerrit=False,
                        include_comment=config.GERRIT_INCLUDE_COMMENT
                    )
                    write_step_summary(github_summary, config.GITHUB_STEP_SUMMARY)
                    logger.info("GitHub summary generated")

                # Generate Gerrit summary (independent of GitHub summary)
                # Always generate when enabled, even if no Gerrit data found
                if config.GERRIT_SUMMARY:
                    logger.info("Generating Gerrit parameters summary...")
                    gerrit_section = markdown_formatter._format_gerrit_section(
                        metadata,
                        include_comment=config.GERRIT_INCLUDE_COMMENT
                    )
                    write_step_summary(gerrit_section + "\n", config.GITHUB_STEP_SUMMARY)
                    logger.info("Gerrit summary generated")

                # Generate Files summary (independent of GitHub summary)
                # Only generate if there are actually changed files to display
                if config.FILES_SUMMARY and metadata.changed_files.count > 0:
                    logger.info("Generating changed files summary...")
                    files_section = markdown_formatter._format_files_section(metadata)
                    write_step_summary(files_section + "\n", config.GITHUB_STEP_SUMMARY)
                    logger.info("Files summary generated")

                # Generate Last Commit Files summary when Gerrit data is present
                # Only generate if there are changed files in last commit and Gerrit data exists
                if (config.GERRIT_SUMMARY and
                    metadata.gerrit_environment.change_id and
                    metadata.changed_files_last_commit.count > 0):
                    logger.info("Generating last commit changed files summary...")
                    last_commit_files_section = markdown_formatter._format_last_commit_files_section(metadata)
                    write_step_summary(last_commit_files_section + "\n", config.GITHUB_STEP_SUMMARY)
                    logger.info("Last commit files summary generated")

            # Generate optional artifacts
            if config.ARTIFACT_UPLOAD:
                logger.info("Generating metadata artifacts...")
                artifact_gen = ArtifactGenerator(config)
                artifact_path = artifact_gen.generate(metadata)

                # Add artifact outputs
                artifact_outputs = {
                    "artifact_path": str(artifact_path),
                    "artifact_suffix": artifact_gen.suffix
                }
                write_github_output(artifact_outputs, config.GITHUB_OUTPUT)
                logger.info(f"Artifacts generated at: {artifact_path}")

            # Print summary to console
            print_summary(metadata)

            logger.info("Repository metadata extraction completed successfully")

        return 0

    except MetadataExtractionError as e:
        logger.error(f"Metadata extraction error: {e}")
        print(f"❌ ERROR: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.error(f"Unexpected error during metadata extraction: {e}", exc_info=True)
        print(f"❌ FATAL ERROR: {e}", file=sys.stderr)
        return 1


class _NullContextManager:
    """Null context manager for when GitHub API is not initialized."""
    def __enter__(self) -> None:
        return None
    def __exit__(self, exc_type, exc_val, exc_tb) -> Literal[False]:
        return False


if __name__ == "__main__":
    sys.exit(main())
