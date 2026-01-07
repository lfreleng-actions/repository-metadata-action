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
        sections.append("## 😈 GitHub Environment")
        sections.append("")

        # Repository section
        repo_data = {
            "repository_owner": metadata.repository.owner,
            "repository_name": metadata.repository.name,
            "repository_full_name": metadata.repository.full_name,
            "is_public": str(metadata.repository.is_public).lower(),
            "is_private": str(metadata.repository.is_private).lower(),
        }
        sections.extend(self._format_table("Repository", repo_data))

        # Event section
        event_data = {
            "event_name": metadata.event.name,
            "tag_push_event": str(metadata.event.tag_push_event).lower(),
            "is_tag_push": str(metadata.event.is_tag_push).lower(),
            "is_branch_push": str(metadata.event.is_branch_push).lower(),
            "is_pull_request": str(metadata.event.is_pull_request).lower(),
            "is_release": str(metadata.event.is_release).lower(),
            "is_schedule": str(metadata.event.is_schedule).lower(),
            "is_workflow_dispatch": str(metadata.event.is_workflow_dispatch).lower(),
        }
        sections.extend(self._format_table("Event Type", event_data))

        # Branch/Tag section
        ref_data = {
            "branch_name": metadata.ref.branch_name or '',
            "tag_name": metadata.ref.tag_name or '',
            "is_default_branch": str(metadata.ref.is_default_branch).lower(),
            "is_main_branch": str(metadata.ref.is_main_branch).lower(),
        }
        sections.extend(self._format_table("Branch/Tag", ref_data))

        # Commit section
        commit_data = {
            "commit_sha": metadata.commit.sha,
            "commit_sha_short": metadata.commit.sha_short,
            "commit_message": metadata.commit.message or '',
            "commit_author": metadata.commit.author or '',
        }
        sections.extend(self._format_table("Commit", commit_data))

        # Pull Request section
        pr_data = {
            "pr_number": str(metadata.pull_request.number) if metadata.pull_request.number else '',
            "pr_source_branch": metadata.pull_request.source_branch or '',
            "pr_target_branch": metadata.pull_request.target_branch or '',
            "is_fork": str(metadata.pull_request.is_fork).lower(),
            "pr_commits_count": str(metadata.pull_request.commits_count) if metadata.pull_request.commits_count else '',
        }
        sections.extend(self._format_table("Pull Request", pr_data))

        # Actor section
        actor_data = {
            "actor": metadata.actor.name,
            "actor_id": str(metadata.actor.id) if metadata.actor.id else '',
        }
        sections.extend(self._format_table("Actor", actor_data))

        # Cache section
        cache_data = {
            "cache_key": metadata.cache.key,
            "cache_restore_key": metadata.cache.restore_key,
        }
        sections.extend(self._format_table("Cache", cache_data))

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

        lines.append("## ℹ️ Gerrit Parameters")
        lines.append("")

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
            # Use shared table formatting
            gerrit_data = {name: str(value) for name, value in populated_fields}
            table_lines = self._format_table("", gerrit_data)
            # Remove the title line since we already have "## 📋 Gerrit Parameters"
            # and remove empty lines at beginning
            if table_lines:
                # Skip the first two lines (title and empty line) from _format_table
                lines.extend(table_lines[2:])
            else:
                lines.append("")

        return "\n".join(lines)

    def _format_files_section(self, metadata: "CompleteMetadata") -> str:
        """
        Format changed files section.

        Args:
            metadata: CompleteMetadata object containing changed files data

        Returns:
            Formatted changed files section as markdown string
        """
        changed_files = metadata.changed_files
        lines = []

        lines.append("## 📁 Changed Files")
        lines.append("")

        # Check if there are any changed files
        if not changed_files or changed_files.count == 0:
            lines.append("⚠️ No changed files detected")
            lines.append("")
            return "\n".join(lines)

        # Summary counts
        lines.append(f"**Total Changed Files:** {changed_files.count}")
        lines.append("")

        # Categorized counts table
        if changed_files.added_count > 0 or changed_files.modified_count > 0 or changed_files.removed_count > 0:
            lines.append("| Category | Count |")
            lines.append("| -------- | ----- |")
            if changed_files.added_count > 0:
                lines.append(f"| ✅ Added | {changed_files.added_count} |")
            if changed_files.modified_count > 0:
                lines.append(f"| ✏️ Modified | {changed_files.modified_count} |")
            if changed_files.removed_count > 0:
                lines.append(f"| ❌ Removed | {changed_files.removed_count} |")
            lines.append("")

        # File lists (show up to 50 files per category to avoid excessive output)
        max_files_to_show = 50

        if changed_files.added:
            lines.append("### ✅ Added Files")
            lines.append("")
            for file in changed_files.added[:max_files_to_show]:
                lines.append(f"- `{self._escape_markdown(file)}`")
            if len(changed_files.added) > max_files_to_show:
                lines.append(f"- ... and {len(changed_files.added) - max_files_to_show} more")
            lines.append("")

        if changed_files.modified:
            lines.append("### ✏️ Modified Files")
            lines.append("")
            for file in changed_files.modified[:max_files_to_show]:
                lines.append(f"- `{self._escape_markdown(file)}`")
            if len(changed_files.modified) > max_files_to_show:
                lines.append(f"- ... and {len(changed_files.modified) - max_files_to_show} more")
            lines.append("")

        if changed_files.removed:
            lines.append("### ❌ Removed Files")
            lines.append("")
            for file in changed_files.removed[:max_files_to_show]:
                lines.append(f"- `{self._escape_markdown(file)}`")
            if len(changed_files.removed) > max_files_to_show:
                lines.append(f"- ... and {len(changed_files.removed) - max_files_to_show} more")
            lines.append("")

        return "\n".join(lines)

    def _format_last_commit_files_section(self, metadata: "CompleteMetadata") -> str:
        """
        Format changed files from last commit section.

        Args:
            metadata: CompleteMetadata object containing last commit changed files data

        Returns:
            Formatted last commit changed files section as markdown string
        """
        changed_files = metadata.changed_files_last_commit
        lines = []

        lines.append("## 📁 Changed Files (Last Commit)")
        lines.append("")

        # Check if there are any changed files
        if not changed_files or changed_files.count == 0:
            lines.append("⚠️ No changed files detected in last commit")
            lines.append("")
            return "\n".join(lines)

        # Summary counts
        lines.append(f"**Total Changed Files:** {changed_files.count}")
        lines.append("")

        # Categorized counts table
        if changed_files.added_count > 0 or changed_files.modified_count > 0 or changed_files.removed_count > 0:
            lines.append("| Category | Count |")
            lines.append("| -------- | ----- |")
            if changed_files.added_count > 0:
                lines.append(f"| ✅ Added | {changed_files.added_count} |")
            if changed_files.modified_count > 0:
                lines.append(f"| ✏️ Modified | {changed_files.modified_count} |")
            if changed_files.removed_count > 0:
                lines.append(f"| ❌ Removed | {changed_files.removed_count} |")
            lines.append("")

        # File lists (show up to 50 files per category to avoid excessive output)
        max_files_to_show = 50

        if changed_files.added:
            lines.append("### ✅ Added Files")
            lines.append("")
            for file in changed_files.added[:max_files_to_show]:
                lines.append(f"- `{self._escape_markdown(file)}`")
            if len(changed_files.added) > max_files_to_show:
                lines.append(f"- ... and {len(changed_files.added) - max_files_to_show} more")
            lines.append("")

        if changed_files.modified:
            lines.append("### ✏️ Modified Files")
            lines.append("")
            for file in changed_files.modified[:max_files_to_show]:
                lines.append(f"- `{self._escape_markdown(file)}`")
            if len(changed_files.modified) > max_files_to_show:
                lines.append(f"- ... and {len(changed_files.modified) - max_files_to_show} more")
            lines.append("")

        if changed_files.removed:
            lines.append("### ❌ Removed Files")
            lines.append("")
            for file in changed_files.removed[:max_files_to_show]:
                lines.append(f"- `{self._escape_markdown(file)}`")
            if len(changed_files.removed) > max_files_to_show:
                lines.append(f"- ... and {len(changed_files.removed) - max_files_to_show} more")
            lines.append("")

        return "\n".join(lines)

    def _format_table(self, title: str, data: dict[str, str]) -> list[str]:
        """
        Format a markdown table with property/value pairs, filtering out empty values.

        Args:
            title: Section title (e.g., "Repository", "Actor")
            data: Dictionary of property names to values

        Returns:
            List of formatted lines for the table section
        """
        lines: list[str] = []

        # Filter out empty values
        populated_data = {k: v for k, v in data.items() if v}

        # If no data to show, return empty list
        if not populated_data:
            return lines

        lines.append(f"### {title}")
        lines.append("")
        lines.append("| Property | Value |")
        lines.append("| -------- | ----- |")

        for key, value in populated_data.items():
            # Escape markdown special characters in values
            safe_value = self._escape_markdown(str(value))
            lines.append(f"| {key} | `{safe_value}` |")

        lines.append("")
        return lines

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
