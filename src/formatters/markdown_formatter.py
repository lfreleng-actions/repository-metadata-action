# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Markdown formatter for GitHub Step Summary.
Generates formatted markdown output for the action summary.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import CompleteMetadata


class MarkdownFormatter:
    """Formats metadata as Markdown for GitHub Step Summary."""

    def format(self, metadata: "CompleteMetadata", include_gerrit: bool = False, include_comment: bool = False) -> str:
        """
        Format metadata as Markdown.

        Args:
            metadata: CompleteMetadata object to format
            include_gerrit: Whether to include Gerrit section
            include_comment: Whether to include Gerrit comment field (default: False for security)

        Returns:
            Markdown string suitable for GitHub Step Summary
        """
        sections = []

        # Header
        sections.append("## Repository Metadata\n")

        # Repository section
        sections.append("### 📦 Repository Outputs")
        sections.append(f"✅ repository_owner: {metadata.repository.owner}")
        sections.append(f"✅ repository_name: {metadata.repository.name}")
        sections.append(f"✅ repository_full_name: {metadata.repository.full_name}")
        sections.append(f"✅ is_public: {str(metadata.repository.is_public).lower()}")
        sections.append(f"✅ is_private: {str(metadata.repository.is_private).lower()}")
        sections.append("")

        # Event section
        sections.append("### 🎯 Event Type Outputs")
        sections.append(f"✅ event_name: {metadata.event.name}")
        sections.append(f"✅ tag_push_event: {str(metadata.event.tag_push_event).lower()}")
        sections.append(f"✅ is_tag_push: {str(metadata.event.is_tag_push).lower()}")
        sections.append(f"✅ is_branch_push: {str(metadata.event.is_branch_push).lower()}")
        sections.append(f"✅ is_pull_request: {str(metadata.event.is_pull_request).lower()}")
        sections.append(f"✅ is_release: {str(metadata.event.is_release).lower()}")
        sections.append(f"✅ is_schedule: {str(metadata.event.is_schedule).lower()}")
        sections.append(f"✅ is_workflow_dispatch: {str(metadata.event.is_workflow_dispatch).lower()}")
        sections.append("")

        # Branch/Tag section
        sections.append("### 🔀 Branch/Tag Outputs")
        sections.append(f"✅ branch_name: {metadata.ref.branch_name or ''}")
        sections.append(f"✅ tag_name: {metadata.ref.tag_name or ''}")
        sections.append(f"✅ is_default_branch: {str(metadata.ref.is_default_branch).lower()}")
        sections.append(f"✅ is_main_branch: {str(metadata.ref.is_main_branch).lower()}")
        sections.append("")

        # Commit section
        sections.append("### 📝 Commit Outputs")
        sections.append(f"✅ commit_sha: {metadata.commit.sha}")
        sections.append(f"✅ commit_sha_short: {metadata.commit.sha_short}")
        sections.append(f"✅ commit_message: {metadata.commit.message or ''}")
        sections.append(f"✅ commit_author: {metadata.commit.author or ''}")
        sections.append("")

        # Pull Request section
        sections.append("### 🔄 Pull Request Outputs")
        sections.append(f"✅ pr_number: {metadata.pull_request.number or ''}")
        sections.append(f"✅ pr_source_branch: {metadata.pull_request.source_branch or ''}")
        sections.append(f"✅ pr_target_branch: {metadata.pull_request.target_branch or ''}")
        sections.append(f"✅ is_fork: {str(metadata.pull_request.is_fork).lower()}")
        sections.append(f"✅ pr_commits_count: {metadata.pull_request.commits_count or ''}")
        sections.append("")

        # Actor section
        sections.append("### 👤 Actor Outputs")
        sections.append(f"✅ actor: {metadata.actor.name}")
        sections.append(f"✅ actor_id: {metadata.actor.id or ''}")
        sections.append("")

        # Cache section
        sections.append("### 🔑 Cache Outputs")
        sections.append(f"✅ cache_key: {metadata.cache.key}")
        sections.append(f"✅ cache_restore_key: {metadata.cache.restore_key}")
        sections.append("")

        # Changed Files section
        sections.append("### 📄 Changed Files Outputs")
        sections.append(f"✅ changed_files_count: {metadata.changed_files.count}")
        if metadata.changed_files.files:
            sections.append("")
            sections.append("First 10 changed files:")
            for file in metadata.changed_files.files[:10]:
                # Escape special markdown characters
                safe_file = self._escape_markdown(file)
                sections.append(f"  - `{safe_file}`")
        sections.append("")

        # Gerrit section (optional)
        if include_gerrit and metadata.gerrit_environment:
            sections.append(self._format_gerrit_section(metadata, include_comment=include_comment))

        return "\n".join(sections)

    def _format_gerrit_section(self, metadata: "CompleteMetadata", include_comment: bool = False) -> str:
        """
        Format Gerrit parameters section.

        Args:
            metadata: CompleteMetadata object containing Gerrit data
            include_comment: Whether to include Gerrit comment field (default: False for security)

        Returns:
            Formatted Gerrit section as markdown string
        """
        gerrit = metadata.gerrit_environment
        lines = []

        lines.append("## 📋 Gerrit Parameters")
        lines.append("")

        # Helper to sanitize values for table
        def sanitize(value):
            if not value:
                return ""
            # Escape pipes and backticks
            return str(value).replace("|", "\\|").replace("`", "\\`")

        # Define all fields to check
        fields = [
            ("branch", gerrit.branch),
            ("change_id", gerrit.change_id),
            ("change_number", gerrit.change_number),
            ("change_url", gerrit.change_url),
            ("event_type", gerrit.event_type),
            ("patchset_number", gerrit.patchset_number),
            ("patchset_revision", gerrit.patchset_revision),
            ("project", gerrit.project),
            ("refspec", gerrit.refspec),
        ]

        # Add comment to fields if explicitly requested (security concern)
        if include_comment and gerrit.comment:
            comment = gerrit.comment
            if len(comment) > 200:
                comment = comment[:200] + "..."
            fields.append(("comment", comment))

        # Filter to only populated fields
        populated_fields = [(name, value) for name, value in fields if value]

        # If no Gerrit data found, show warning message and no table
        if not populated_fields and gerrit.source == "none":
            lines.append("⚠️ No Gerrit metadata found in workflow/execution environment")
            lines.append("")
            return "\n".join(lines)

        # Add source information if available
        if gerrit.source and gerrit.source != "none":
            lines.append(f"Source: {gerrit.source}")
            lines.append("")

        # Only show table if there are populated fields
        if populated_fields:
            lines.append("| Gerrit Change Property | Value |")
            lines.append("| ---------------------- | ----- |")

            # Add only rows with populated values
            for field_name, field_value in populated_fields:
                lines.append(f"| {field_name} | `{sanitize(field_value)}` |")

        lines.append("")

        return "\n".join(lines)

    def _escape_markdown(self, text: str) -> str:
        """
        Escape special markdown characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text safe for markdown
        """
        # Escape backticks and pipes
        return text.replace("`", "\\`").replace("|", "\\|")
