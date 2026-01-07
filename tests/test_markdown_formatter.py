# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for MarkdownFormatter.
"""

import pytest

from src.formatters.markdown_formatter import MarkdownFormatter
from src.models import (
    ActorMetadata,
    CacheMetadata,
    ChangedFilesMetadata,
    CommitMetadata,
    CompleteMetadata,
    EventMetadata,
    GerritMetadata,
    PullRequestMetadata,
    RefMetadata,
    RepositoryMetadata,
)


class TestMarkdownFormatter:
    """Tests for MarkdownFormatter class."""

    @pytest.fixture
    def formatter(self):
        """Create a markdown formatter instance."""
        return MarkdownFormatter()

    @pytest.fixture
    def basic_metadata(self):
        """Create basic metadata for testing."""
        return CompleteMetadata(
            repository=RepositoryMetadata(
                owner="test-owner",
                name="test-repo",
                full_name="test-owner/test-repo",
                is_public=True,
                is_private=False,
            ),
            event=EventMetadata(name="push", is_branch_push=True),
            ref=RefMetadata(branch_name="main", is_main_branch=True),
            commit=CommitMetadata(
                sha="a" * 40, sha_short="a" * 7, message="Test commit", author="Test Author"
            ),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="testuser", id=12345),
            cache=CacheMetadata(key="test-key", restore_key="test-restore"),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(),
            gerrit_environment=GerritMetadata(
                branch="",
                change_id="",
                change_number="",
                change_url="",
                event_type="",
                patchset_number="",
                patchset_revision="",
                project="",
                refspec="",
                comment="",
                source="none",
            ),
        )

    @pytest.fixture
    def metadata_with_gerrit(self):
        """Create metadata with Gerrit data."""
        return CompleteMetadata(
            repository=RepositoryMetadata(
                owner="lfit", name="sandbox", full_name="lfit/sandbox", is_public=True
            ),
            event=EventMetadata(name="workflow_dispatch", is_workflow_dispatch=True),
            ref=RefMetadata(branch_name="master", is_main_branch=True),
            commit=CommitMetadata(
                sha="79f418203e93ab4bc0e7879c7a4f634d41f08087", sha_short="79f4182"
            ),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="lfit-replication", id=29716385),
            cache=CacheMetadata(
                key="lfit-sandbox-master-79f4182", restore_key="lfit-sandbox-master-"
            ),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(),
            gerrit_environment=GerritMetadata(
                branch="master",
                change_id="Ib2e87d192c88da6250951ea96d96c2a845ffee55",
                change_number="74048",
                change_url="https://gerrit.linuxfoundation.org/infra/c/sandbox/+/74048",
                event_type="change-merged",
                patchset_number="1",
                patchset_revision="d6968c385531c3523a69a8e673c390ac6af849a9",
                project="sandbox",
                refspec="refs/heads/master",
            ),
        )

    def test_format_basic(self, formatter, basic_metadata):
        """Test basic markdown formatting."""
        result = formatter.format(basic_metadata)

        assert isinstance(result, str)
        assert "## 😈 GitHub Environment" in result
        assert "### Repository" in result
        assert "### Event Type" in result
        assert "### Branch/Tag" in result
        assert "### Commit" in result
        assert "### Actor" in result
        assert "### Cache" in result

    def test_format_includes_repository_data(self, formatter, basic_metadata):
        """Test that repository data is included."""
        result = formatter.format(basic_metadata)

        assert "test-owner" in result
        assert "test-repo" in result
        assert "test-owner/test-repo" in result

    def test_format_includes_commit_data(self, formatter, basic_metadata):
        """Test that commit data is included."""
        result = formatter.format(basic_metadata)

        assert "a" * 7 in result  # short SHA
        assert "Test commit" in result
        assert "Test Author" in result

    def test_format_includes_actor_data(self, formatter, basic_metadata):
        """Test that actor data is included."""
        result = formatter.format(basic_metadata)

        assert "testuser" in result
        assert "12345" in result

    def test_format_gerrit_section(self, formatter, metadata_with_gerrit):
        """Test formatting Gerrit section."""
        result = formatter._format_gerrit_section(metadata_with_gerrit)

        assert "Gerrit Parameters" in result
        assert "Ib2e87d192c88da6250951ea96d96c2a845ffee55" in result
        assert "74048" in result
        assert "change-merged" in result
        assert "sandbox" in result

    def test_format_gerrit_section_with_url(self, formatter, metadata_with_gerrit):
        """Test Gerrit section includes URL."""
        result = formatter._format_gerrit_section(metadata_with_gerrit)

        assert "https://gerrit.linuxfoundation.org/infra/c/sandbox/+/74048" in result

    def test_format_gerrit_section_no_data(self, formatter, basic_metadata):
        """Test Gerrit section when no data present."""
        result = formatter._format_gerrit_section(basic_metadata)

        assert "Gerrit Parameters" in result
        assert "No Gerrit metadata found" in result

    def test_format_files_section_empty(self, formatter, basic_metadata):
        """Test files section when no files changed."""
        result = formatter._format_files_section(basic_metadata)

        assert "## 📁 Changed Files" in result
        assert "No changed files detected" in result

    def test_format_files_section_with_files(self, formatter, basic_metadata):
        """Test files section with changed files."""
        basic_metadata.changed_files = ChangedFilesMetadata(
            files=["file1.py", "file2.py", "file3.py"],
            added=["file1.py"],
            modified=["file2.py"],
            removed=["file3.py"],
        )

        result = formatter._format_files_section(basic_metadata)

        assert "## 📁 Changed Files" in result
        assert "**Total Changed Files:** 3" in result
        assert "✅ Added" in result
        assert "✏️ Modified" in result
        assert "❌ Removed" in result
        assert "file1.py" in result
        assert "file2.py" in result
        assert "file3.py" in result

    def test_escape_markdown(self, formatter):
        """Test markdown escaping."""
        text = "file|with|pipes.txt"
        result = formatter._escape_markdown(text)
        assert "\\|" in result

        text = "file`with`backticks.txt"
        result = formatter._escape_markdown(text)
        assert "\\`" in result


class TestMarkdownFormatterLastCommit:
    """Tests for last commit files section formatting."""

    @pytest.fixture
    def formatter(self):
        """Create a markdown formatter instance."""
        return MarkdownFormatter()

    @pytest.fixture
    def metadata_with_last_commit(self):
        """Create metadata with last commit files."""
        return CompleteMetadata(
            repository=RepositoryMetadata(
                owner="lfit", name="sandbox", full_name="lfit/sandbox", is_public=True
            ),
            event=EventMetadata(name="workflow_dispatch", is_workflow_dispatch=True),
            ref=RefMetadata(branch_name="master", is_main_branch=True),
            commit=CommitMetadata(
                sha="79f418203e93ab4bc0e7879c7a4f634d41f08087", sha_short="79f4182"
            ),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="lfit-replication", id=29716385),
            cache=CacheMetadata(
                key="lfit-sandbox-master-79f4182", restore_key="lfit-sandbox-master-"
            ),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(
                files=["README.md", "test.txt"],
                added=["test.txt"],
                modified=["README.md"],
                removed=[],
            ),
            gerrit_environment=GerritMetadata(
                branch="master",
                change_id="Ib2e87d192c88da6250951ea96d96c2a845ffee55",
                change_number="74048",
            ),
        )

    def test_format_last_commit_files_basic(self, formatter, metadata_with_last_commit):
        """Test basic rendering with mixed file types."""
        result = formatter._format_last_commit_files_section(metadata_with_last_commit)

        assert "## 📁 Changed Files (Last Commit)" in result
        assert "**Total Changed Files:** 2" in result
        assert "✅ Added" in result
        assert "✏️ Modified" in result
        assert "README.md" in result
        assert "test.txt" in result

    def test_format_last_commit_files_empty(self, formatter):
        """Test rendering when no files changed."""
        metadata = CompleteMetadata(
            repository=RepositoryMetadata(
                owner="test", name="repo", full_name="test/repo", is_public=True
            ),
            event=EventMetadata(name="push", is_branch_push=True),
            ref=RefMetadata(branch_name="main"),
            commit=CommitMetadata(sha="a" * 40, sha_short="a" * 7),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="tester"),
            cache=CacheMetadata(key="key", restore_key="restore"),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(),
            gerrit_environment=GerritMetadata(),
        )

        result = formatter._format_last_commit_files_section(metadata)

        assert "## 📁 Changed Files (Last Commit)" in result
        assert "No changed files detected in last commit" in result

    def test_format_last_commit_files_only_added(self, formatter):
        """Test rendering with only added files."""
        metadata = CompleteMetadata(
            repository=RepositoryMetadata(
                owner="test", name="repo", full_name="test/repo", is_public=True
            ),
            event=EventMetadata(name="push", is_branch_push=True),
            ref=RefMetadata(branch_name="main"),
            commit=CommitMetadata(sha="a" * 40, sha_short="a" * 7),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="tester"),
            cache=CacheMetadata(key="key", restore_key="restore"),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(
                files=["new1.py", "new2.py", "new3.py"],
                added=["new1.py", "new2.py", "new3.py"],
                modified=[],
                removed=[],
            ),
            gerrit_environment=GerritMetadata(),
        )

        result = formatter._format_last_commit_files_section(metadata)

        assert "**Total Changed Files:** 3" in result
        assert "✅ Added" in result
        assert "| ✅ Added | 3 |" in result
        assert "### ✅ Added Files" in result
        # Should NOT show modified or removed sections
        assert "✏️ Modified" not in result or "| ✏️ Modified | 0 |" not in result
        assert "❌ Removed" not in result or "| ❌ Removed | 0 |" not in result

    def test_format_last_commit_files_only_modified(self, formatter):
        """Test rendering with only modified files."""
        metadata = CompleteMetadata(
            repository=RepositoryMetadata(
                owner="test", name="repo", full_name="test/repo", is_public=True
            ),
            event=EventMetadata(name="push", is_branch_push=True),
            ref=RefMetadata(branch_name="main"),
            commit=CommitMetadata(sha="a" * 40, sha_short="a" * 7),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="tester"),
            cache=CacheMetadata(key="key", restore_key="restore"),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(
                files=["existing1.py", "existing2.py"],
                added=[],
                modified=["existing1.py", "existing2.py"],
                removed=[],
            ),
            gerrit_environment=GerritMetadata(),
        )

        result = formatter._format_last_commit_files_section(metadata)

        assert "**Total Changed Files:** 2" in result
        assert "✏️ Modified" in result
        assert "| ✏️ Modified | 2 |" in result
        assert "### ✏️ Modified Files" in result

    def test_format_last_commit_files_only_removed(self, formatter):
        """Test rendering with only removed files."""
        metadata = CompleteMetadata(
            repository=RepositoryMetadata(
                owner="test", name="repo", full_name="test/repo", is_public=True
            ),
            event=EventMetadata(name="push", is_branch_push=True),
            ref=RefMetadata(branch_name="main"),
            commit=CommitMetadata(sha="a" * 40, sha_short="a" * 7),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="tester"),
            cache=CacheMetadata(key="key", restore_key="restore"),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(
                files=["deleted.py"], added=[], modified=[], removed=["deleted.py"]
            ),
            gerrit_environment=GerritMetadata(),
        )

        result = formatter._format_last_commit_files_section(metadata)

        assert "**Total Changed Files:** 1" in result
        assert "❌ Removed" in result
        assert "| ❌ Removed | 1 |" in result
        assert "### ❌ Removed Files" in result

    def test_format_last_commit_files_truncation(self, formatter):
        """Test file list truncation at 50 files."""
        # Create 60 added files
        many_files = [f"file{i}.py" for i in range(60)]

        metadata = CompleteMetadata(
            repository=RepositoryMetadata(
                owner="test", name="repo", full_name="test/repo", is_public=True
            ),
            event=EventMetadata(name="push", is_branch_push=True),
            ref=RefMetadata(branch_name="main"),
            commit=CommitMetadata(sha="a" * 40, sha_short="a" * 7),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="tester"),
            cache=CacheMetadata(key="key", restore_key="restore"),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(
                files=many_files, added=many_files, modified=[], removed=[]
            ),
            gerrit_environment=GerritMetadata(),
        )

        result = formatter._format_last_commit_files_section(metadata)

        assert "**Total Changed Files:** 60" in result
        assert "... and 10 more" in result
        # Should show first 50 files
        assert "file0.py" in result
        assert "file49.py" in result
        # But not the last 10
        assert "file59.py" not in result

    def test_format_last_commit_files_special_chars(self, formatter):
        """Test markdown escaping (pipes, backticks)."""
        metadata = CompleteMetadata(
            repository=RepositoryMetadata(
                owner="test", name="repo", full_name="test/repo", is_public=True
            ),
            event=EventMetadata(name="push", is_branch_push=True),
            ref=RefMetadata(branch_name="main"),
            commit=CommitMetadata(sha="a" * 40, sha_short="a" * 7),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="tester"),
            cache=CacheMetadata(key="key", restore_key="restore"),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(
                files=["file|with|pipes.txt", "file`with`backticks.txt"],
                added=["file|with|pipes.txt"],
                modified=["file`with`backticks.txt"],
                removed=[],
            ),
            gerrit_environment=GerritMetadata(),
        )

        result = formatter._format_last_commit_files_section(metadata)

        # Pipes should be escaped
        assert "file\\|with\\|pipes.txt" in result
        # Backticks should be escaped
        assert "file\\`with\\`backticks.txt" in result

    def test_format_last_commit_files_unicode(self, formatter):
        """Test unicode filenames."""
        metadata = CompleteMetadata(
            repository=RepositoryMetadata(
                owner="test", name="repo", full_name="test/repo", is_public=True
            ),
            event=EventMetadata(name="push", is_branch_push=True),
            ref=RefMetadata(branch_name="main"),
            commit=CommitMetadata(sha="a" * 40, sha_short="a" * 7),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="tester"),
            cache=CacheMetadata(key="key", restore_key="restore"),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(
                files=["文件.txt", "archivo.py", "файл.js"],
                added=["文件.txt"],
                modified=["archivo.py"],
                removed=["файл.js"],
            ),
            gerrit_environment=GerritMetadata(),
        )

        result = formatter._format_last_commit_files_section(metadata)

        assert "文件.txt" in result
        assert "archivo.py" in result
        assert "файл.js" in result

    def test_format_last_commit_files_counts_table(self, formatter, metadata_with_last_commit):
        """Test that category counts table is formatted correctly."""
        result = formatter._format_last_commit_files_section(metadata_with_last_commit)

        # Check table structure
        assert "| Category | Count |" in result
        assert "| -------- | ----- |" in result
        assert "| ✅ Added | 1 |" in result
        assert "| ✏️ Modified | 1 |" in result

    def test_format_last_commit_files_sections_present(self, formatter, metadata_with_last_commit):
        """Test that file list sections are present."""
        result = formatter._format_last_commit_files_section(metadata_with_last_commit)

        assert "### ✅ Added Files" in result
        assert "### ✏️ Modified Files" in result
        # Removed section should not be present (empty)
        assert "### ❌ Removed Files" not in result


class TestMarkdownFormatterTable:
    """Tests for table formatting helper."""

    @pytest.fixture
    def formatter(self):
        """Create a markdown formatter instance."""
        return MarkdownFormatter()

    def test_format_table_basic(self, formatter):
        """Test basic table formatting."""
        data = {"key1": "value1", "key2": "value2"}
        result = formatter._format_table("Test Section", data)

        assert "### Test Section" in result
        assert "| Property | Value |" in result
        assert "| -------- | ----- |" in result
        assert "| key1 | `value1` |" in result
        assert "| key2 | `value2` |" in result

    def test_format_table_filters_empty_values(self, formatter):
        """Test that empty values are filtered out."""
        data = {"key1": "value1", "key2": "", "key3": "value3"}
        result = formatter._format_table("Test Section", data)

        # Result is a list of lines, join to check
        result_str = "\n".join(result)

        # Should include non-empty values
        assert "key1" in result_str
        assert "value1" in result_str
        assert "key3" in result_str
        assert "value3" in result_str

        # Should not include empty key
        assert "key2" not in result_str

    def test_format_table_all_empty_returns_empty(self, formatter):
        """Test that table with all empty values returns empty list."""
        data = {"key1": "", "key2": "", "key3": ""}
        result = formatter._format_table("Test Section", data)

        assert result == []

    def test_format_table_escapes_values(self, formatter):
        """Test that table values are escaped."""
        data = {"key": "value|with|pipes"}
        result = formatter._format_table("Test Section", data)

        # Result is a list of lines, join to check
        result_str = "\n".join(result)

        # Should escape the pipes
        assert "value\\|with\\|pipes" in result_str
