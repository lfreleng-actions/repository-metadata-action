# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for main.py module.
Covers orchestration, output generation, and integration flow.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.exceptions import MetadataExtractionError
from src.main import main, print_summary, setup_logging, write_github_output, write_step_summary
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


@pytest.fixture
def sample_metadata():
    """Create sample complete metadata for testing."""
    return CompleteMetadata(
        repository=RepositoryMetadata(
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            is_public=True,
            is_private=False,
        ),
        event=EventMetadata(name="push", action=None, number=None, sender_login="testuser"),
        ref=RefMetadata(
            name="refs/heads/main",
            type="branch",
            protected=False,
            branch_name="main",
            tag_name=None,
        ),
        commit=CommitMetadata(
            sha="a" * 40,
            sha_short="a" * 7,
            message="Test commit",
            author_name="Test Author",
            author_email="test@example.com",
            committer_name="Test Committer",
            committer_email="test@example.com",
            timestamp="2024-01-01T00:00:00Z",
        ),
        pull_request=PullRequestMetadata(
            number=None,
            title=None,
            body=None,
            state=None,
            merged=False,
            draft=False,
            head_ref=None,
            base_ref=None,
            head_sha=None,
            base_sha=None,
            labels=[],
            requested_reviewers=[],
            assignees=[],
            is_fork=False,
        ),
        actor=ActorMetadata(name="testuser", id=None, type="User", email=None),
        cache=CacheMetadata(key="test-cache-key", restore_key="test-restore-key-1"),
        changed_files=ChangedFilesMetadata(
            count=5, files=["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
        ),
        changed_files_last_commit=ChangedFilesMetadata(
            count=5, files=["file1.py", "file2.py", "file3.py", "file4.py", "file5.py"]
        ),
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
def sample_metadata_with_pr():
    """Create sample metadata with pull request data."""
    return CompleteMetadata(
        repository=RepositoryMetadata(
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            is_public=True,
            is_private=False,
        ),
        event=EventMetadata(
            name="pull_request", action="opened", number=123, sender_login="testuser"
        ),
        ref=RefMetadata(
            name="refs/pull/123/merge",
            type="branch",
            protected=False,
            branch_name=None,
            tag_name=None,
        ),
        commit=CommitMetadata(
            sha="b" * 40,
            sha_short="b" * 7,
            message="PR commit",
            author_name="Test Author",
            author_email="test@example.com",
            committer_name="Test Committer",
            committer_email="test@example.com",
            timestamp="2024-01-01T00:00:00Z",
        ),
        pull_request=PullRequestMetadata(
            number=123,
            title="Test PR",
            body="Test PR body",
            state="open",
            merged=False,
            draft=False,
            head_ref="feature-branch",
            base_ref="main",
            head_sha="c" * 40,
            base_sha="d" * 40,
            labels=["bug", "enhancement"],
            requested_reviewers=["reviewer1"],
            assignees=["assignee1"],
            is_fork=False,
        ),
        actor=ActorMetadata(name="testuser", id=12345, type="User", email="test@example.com"),
        cache=CacheMetadata(key="pr-cache-key", restore_key="pr-restore-key"),
        changed_files=ChangedFilesMetadata(count=10, files=[f"file{i}.py" for i in range(10)]),
        changed_files_last_commit=ChangedFilesMetadata(
            count=10, files=[f"file{i}.py" for i in range(10)]
        ),
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
def sample_metadata_with_gerrit():
    """Create sample metadata with Gerrit data."""
    gerrit = GerritMetadata(
        change_id="I1234567890abcdef",
        change_number="12345",
        patchset_number="3",
        project="test-project",
        branch="master",
        topic="test-topic",
        change_owner_name="Test Owner",
        change_owner_email="owner@example.com",
        change_subject="Test change",
        change_url="https://gerrit.example.com/12345",
        patchset_revision="e" * 40,
        commit_message="Test Gerrit commit",
    )

    return CompleteMetadata(
        repository=RepositoryMetadata(
            owner="test-owner",
            name="test-repo",
            full_name="test-owner/test-repo",
            is_public=True,
            is_private=False,
        ),
        event=EventMetadata(name="push", action=None, number=None, sender_login="testuser"),
        ref=RefMetadata(
            name="refs/heads/main",
            type="branch",
            protected=False,
            branch_name="main",
            tag_name=None,
        ),
        commit=CommitMetadata(
            sha="e" * 40,
            sha_short="e" * 7,
            message="Test Gerrit commit",
            author_name="Test Author",
            author_email="test@example.com",
            committer_name="Test Committer",
            committer_email="test@example.com",
            timestamp="2024-01-01T00:00:00Z",
        ),
        pull_request=PullRequestMetadata(
            number=None,
            title=None,
            body=None,
            state=None,
            merged=False,
            draft=False,
            head_ref=None,
            base_ref=None,
            head_sha=None,
            base_sha=None,
            labels=[],
            requested_reviewers=[],
            assignees=[],
            is_fork=False,
        ),
        actor=ActorMetadata(name="testuser", id=None, type="User", email=None),
        cache=CacheMetadata(key="gerrit-cache-key", restore_key="gerrit-restore-key"),
        changed_files=ChangedFilesMetadata(
            count=3, files=["file1.java", "file2.java", "file3.java"]
        ),
        changed_files_last_commit=ChangedFilesMetadata(
            count=3, files=["file1.java", "file2.java", "file3.java"]
        ),
        gerrit_environment=gerrit,
    )


class TestSetupLogging:
    """Test setup_logging function."""

    @patch("src.main.get_config")
    def test_setup_logging_debug_mode(self, mock_get_config):
        """Test logging setup in debug mode."""
        mock_config = Mock()
        mock_config.DEBUG_MODE = True
        mock_get_config.return_value = mock_config

        logger = setup_logging()

        assert logger is not None
        assert logger.name == "repository-metadata"
        assert logger.level <= 10  # DEBUG or lower

    @patch("src.main.get_config")
    def test_setup_logging_info_mode(self, mock_get_config):
        """Test logging setup in info mode."""
        mock_config = Mock()
        mock_config.DEBUG_MODE = False
        mock_get_config.return_value = mock_config

        logger = setup_logging()

        assert logger is not None
        assert logger.name == "repository-metadata"


class TestWriteGitHubOutput:
    """Test write_github_output function."""

    def test_write_single_line_outputs(self):
        """Test writing single-line outputs."""
        outputs: dict[str, str] = {"key1": "value1", "key2": "value2", "key3": "123"}

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            output_file = Path(f.name)

        try:
            write_github_output(outputs, output_file)

            content = output_file.read_text()
            assert "key1=value1" in content
            assert "key2=value2" in content
            assert "key3=123" in content
        finally:
            output_file.unlink()

    def test_write_multiline_outputs(self):
        """Test writing multi-line outputs with delimiters."""
        outputs: dict[str, str] = {"single": "value", "multiline": "line1\nline2\nline3"}

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            output_file = Path(f.name)

        try:
            write_github_output(outputs, output_file)

            content = output_file.read_text()
            assert "single=value" in content
            assert "multiline<<EOF_" in content
            assert "line1\nline2\nline3" in content
            assert content.count("EOF_") == 2  # Opening and closing delimiter
        finally:
            output_file.unlink()

    def test_write_empty_outputs(self):
        """Test writing empty outputs."""
        outputs: dict[str, str] = {}

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            output_file = Path(f.name)

        try:
            write_github_output(outputs, output_file)

            content = output_file.read_text()
            assert content == ""
        finally:
            output_file.unlink()

    def test_write_outputs_append_mode(self):
        """Test that outputs are appended to existing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            output_file = Path(f.name)
            f.write("existing=content\n")

        try:
            outputs = {"new": "value"}
            write_github_output(outputs, output_file)

            content = output_file.read_text()
            assert "existing=content" in content
            assert "new=value" in content
        finally:
            output_file.unlink()


class TestWriteStepSummary:
    """Test write_step_summary function."""

    def test_write_step_summary_with_file(self):
        """Test writing step summary to file."""
        content = "# Test Summary\nThis is a test."

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            summary_file = Path(f.name)

        try:
            write_step_summary(content, summary_file)

            written_content = summary_file.read_text()
            assert written_content == content
        finally:
            summary_file.unlink()

    def test_write_step_summary_without_file(self):
        """Test writing step summary when file is None."""
        content = "# Test Summary\nThis is a test."

        # Should not raise any exception
        write_step_summary(content, None)

    def test_write_step_summary_append_mode(self):
        """Test that summary is appended to existing file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            summary_file = Path(f.name)
            f.write("# Existing Summary\n")

        try:
            content = "## New Section\n"
            write_step_summary(content, summary_file)

            written_content = summary_file.read_text()
            assert "# Existing Summary" in written_content
            assert "## New Section" in written_content
        finally:
            summary_file.unlink()


class TestPrintSummary:
    """Test print_summary function."""

    def test_print_summary_basic(self, sample_metadata, capsys):
        """Test printing basic summary."""
        print_summary(sample_metadata)

        captured = capsys.readouterr()
        assert "Repository Metadata Extraction Complete" in captured.out
        assert "test-owner/test-repo" in captured.out
        assert "push" in captured.out
        assert "testuser" in captured.out
        assert "main" in captured.out
        assert "Changed Files: 5" in captured.out

    def test_print_summary_with_pr(self, sample_metadata_with_pr, capsys):
        """Test printing summary with pull request."""
        print_summary(sample_metadata_with_pr)

        captured = capsys.readouterr()
        assert "test-owner/test-repo" in captured.out
        assert "pull_request" in captured.out
        assert "Pull Request: #123" in captured.out
        assert "Changed Files: 10" in captured.out

    def test_print_summary_with_gerrit(self, sample_metadata_with_gerrit, capsys):
        """Test printing summary with Gerrit metadata."""
        print_summary(sample_metadata_with_gerrit)

        captured = capsys.readouterr()
        assert "test-owner/test-repo" in captured.out
        assert "Gerrit Change-ID: I1234567890abcdef" in captured.out

    def test_print_summary_with_tag(self, sample_metadata, capsys):
        """Test printing summary with tag."""
        sample_metadata.ref.tag_name = "v1.0.0"
        sample_metadata.ref.branch_name = None

        print_summary(sample_metadata)

        captured = capsys.readouterr()
        assert "Tag: v1.0.0" in captured.out


class TestMainFunction:
    """Test main function integration."""

    @patch("src.main.get_config")
    @patch("src.main.GitHubAPI")
    @patch("src.main.GitOperations")
    @patch("src.main.RepositoryExtractor")
    @patch("src.main.EventExtractor")
    @patch("src.main.RefExtractor")
    @patch("src.main.CommitExtractor")
    @patch("src.main.PullRequestExtractor")
    @patch("src.main.ActorExtractor")
    @patch("src.main.CacheExtractor")
    @patch("src.main.ChangedFilesExtractor")
    @patch("src.main.GerritExtractor")
    @patch("src.main.write_github_output")
    def test_main_success_basic(
        self,
        mock_write_output,
        mock_gerrit_ext,
        mock_changed_ext,
        mock_cache_ext,
        mock_actor_ext,
        mock_pr_ext,
        mock_commit_ext,
        mock_ref_ext,
        mock_event_ext,
        mock_repo_ext,
        mock_git_ops,
        mock_github_api,
        mock_get_config,
        sample_metadata,
    ):
        """Test successful main execution with basic metadata."""
        # Setup config
        mock_config = Mock()
        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.DEBUG_MODE = False
        mock_config.GITHUB_OUTPUT = Path("/tmp/output")
        mock_config.GITHUB_SUMMARY = False
        mock_config.GITHUB_STEP_SUMMARY = None
        mock_config.GERRIT_SUMMARY = True
        mock_config.GERRIT_INCLUDE_COMMENT = False
        mock_config.ARTIFACT_UPLOAD = False
        mock_get_config.return_value = mock_config

        # Setup GitHub API with context manager support
        mock_api = Mock()
        mock_api.__enter__ = Mock(return_value=mock_api)
        mock_api.__exit__ = Mock(return_value=False)
        mock_github_api.return_value = mock_api

        # Setup git operations
        mock_git = Mock()
        mock_git.has_git_repo.return_value = True
        mock_git_ops.return_value = mock_git

        # Setup extractors
        mock_repo_ext.return_value.extract.return_value = sample_metadata.repository
        mock_event_ext.return_value.extract.return_value = sample_metadata.event
        mock_ref_ext.return_value.extract.return_value = sample_metadata.ref
        mock_commit_ext.return_value.extract.return_value = sample_metadata.commit
        mock_pr_ext.return_value.extract.return_value = sample_metadata.pull_request
        mock_actor_ext.return_value.extract.return_value = sample_metadata.actor
        mock_cache_ext.return_value.extract.return_value = sample_metadata.cache
        mock_changed_ext.return_value.extract.return_value = sample_metadata.changed_files
        mock_gerrit_ext.return_value.extract.return_value = sample_metadata.gerrit_environment

        # Execute main
        result = main()

        # Verify success
        assert result == 0
        assert mock_write_output.called
        # close() is called via __exit__ in context manager
        assert mock_api.__exit__.called

    @patch("src.main.get_config")
    @patch("src.main.GitHubAPI")
    @patch("src.main.GitOperations")
    @patch("src.main.RepositoryExtractor")
    @patch("src.main.EventExtractor")
    @patch("src.main.RefExtractor")
    @patch("src.main.CommitExtractor")
    @patch("src.main.PullRequestExtractor")
    @patch("src.main.ActorExtractor")
    @patch("src.main.CacheExtractor")
    @patch("src.main.ChangedFilesExtractor")
    @patch("src.main.GerritExtractor")
    @patch("src.main.write_github_output")
    @patch("src.main.write_step_summary")
    def test_main_with_summary(
        self,
        mock_write_summary,
        mock_write_output,
        mock_gerrit_ext,
        mock_changed_ext,
        mock_cache_ext,
        mock_actor_ext,
        mock_pr_ext,
        mock_commit_ext,
        mock_ref_ext,
        mock_event_ext,
        mock_repo_ext,
        mock_git_ops,
        mock_github_api,
        mock_get_config,
        sample_metadata,
    ):
        """Test main execution with summary generation."""
        # Setup config
        mock_config = Mock()
        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.DEBUG_MODE = False
        mock_config.GITHUB_OUTPUT = Path("/tmp/output")
        mock_config.GITHUB_SUMMARY = True
        mock_config.GITHUB_STEP_SUMMARY = Path("/tmp/summary")
        mock_config.GERRIT_SUMMARY = False
        mock_config.ARTIFACT_UPLOAD = False
        mock_get_config.return_value = mock_config

        # Setup GitHub API with context manager support
        mock_api = Mock()
        mock_api.__enter__ = Mock(return_value=mock_api)
        mock_api.__exit__ = Mock(return_value=False)
        mock_github_api.return_value = mock_api

        # Setup git operations
        mock_git = Mock()
        mock_git.has_git_repo.return_value = True
        mock_git_ops.return_value = mock_git

        # Setup extractors
        mock_repo_ext.return_value.extract.return_value = sample_metadata.repository
        mock_event_ext.return_value.extract.return_value = sample_metadata.event
        mock_ref_ext.return_value.extract.return_value = sample_metadata.ref
        mock_commit_ext.return_value.extract.return_value = sample_metadata.commit
        mock_pr_ext.return_value.extract.return_value = sample_metadata.pull_request
        mock_actor_ext.return_value.extract.return_value = sample_metadata.actor
        mock_cache_ext.return_value.extract.return_value = sample_metadata.cache
        mock_changed_ext.return_value.extract.return_value = sample_metadata.changed_files
        mock_gerrit_ext.return_value.extract.return_value = sample_metadata.gerrit_environment

        # Execute main
        result = main()

        # Verify success and summary was written
        assert result == 0
        assert mock_write_summary.called

    @patch("src.main.get_config")
    @patch("src.main.GitHubAPI")
    @patch("src.main.GitOperations")
    @patch("src.main.RepositoryExtractor")
    @patch("src.main.EventExtractor")
    @patch("src.main.RefExtractor")
    @patch("src.main.CommitExtractor")
    @patch("src.main.PullRequestExtractor")
    @patch("src.main.ActorExtractor")
    @patch("src.main.CacheExtractor")
    @patch("src.main.ChangedFilesExtractor")
    @patch("src.main.GerritExtractor")
    @patch("src.main.write_github_output")
    @patch("src.main.ArtifactGenerator")
    def test_main_with_artifacts(
        self,
        mock_artifact_gen_class,
        mock_write_output,
        mock_gerrit_ext,
        mock_changed_ext,
        mock_cache_ext,
        mock_actor_ext,
        mock_pr_ext,
        mock_commit_ext,
        mock_ref_ext,
        mock_event_ext,
        mock_repo_ext,
        mock_git_ops,
        mock_github_api,
        mock_get_config,
        sample_metadata,
    ):
        """Test main execution with artifact generation."""
        # Setup config
        mock_config = Mock()
        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.DEBUG_MODE = False
        mock_config.GITHUB_OUTPUT = Path("/tmp/output")
        mock_config.GITHUB_SUMMARY = False
        mock_config.GITHUB_STEP_SUMMARY = None
        mock_config.GERRIT_SUMMARY = False
        mock_config.GERRIT_INCLUDE_COMMENT = False
        mock_config.ARTIFACT_UPLOAD = True
        mock_get_config.return_value = mock_config

        # Setup GitHub API with context manager support
        mock_api = Mock()
        mock_api.__enter__ = Mock(return_value=mock_api)
        mock_api.__exit__ = Mock(return_value=False)
        mock_github_api.return_value = mock_api

        # Setup git operations
        mock_git = Mock()
        mock_git.has_git_repo.return_value = True
        mock_git_ops.return_value = mock_git

        # Setup extractors
        mock_repo_ext.return_value.extract.return_value = sample_metadata.repository
        mock_event_ext.return_value.extract.return_value = sample_metadata.event
        mock_ref_ext.return_value.extract.return_value = sample_metadata.ref
        mock_commit_ext.return_value.extract.return_value = sample_metadata.commit
        mock_pr_ext.return_value.extract.return_value = sample_metadata.pull_request
        mock_actor_ext.return_value.extract.return_value = sample_metadata.actor
        mock_cache_ext.return_value.extract.return_value = sample_metadata.cache
        mock_changed_ext.return_value.extract.return_value = sample_metadata.changed_files
        mock_gerrit_ext.return_value.extract.return_value = sample_metadata.gerrit_environment

        # Setup artifact generator
        mock_artifact_gen = Mock()
        mock_artifact_gen.suffix = "test-suffix-12345678"
        mock_artifact_gen.generate.return_value = Path("/tmp/artifacts")
        mock_artifact_gen_class.return_value = mock_artifact_gen

        # Execute main
        result = main()

        # Verify success and artifacts were generated
        assert result == 0
        assert mock_artifact_gen.generate.called
        # Verify artifact outputs were written
        assert mock_write_output.call_count >= 2  # Initial outputs + artifact outputs

    @patch("src.main.get_config")
    @patch("src.main.RepositoryExtractor")
    def test_main_metadata_extraction_error(self, mock_repo_ext, mock_get_config):
        """Test main handles MetadataExtractionError."""
        # Setup config
        mock_config = Mock()
        mock_config.GITHUB_TOKEN = None
        mock_config.DEBUG_MODE = False
        mock_get_config.return_value = mock_config

        # Setup extractor to raise error
        mock_repo_ext.return_value.extract.side_effect = MetadataExtractionError("Test error")

        # Execute main
        result = main()

        # Verify error handling
        assert result == 1

    @patch("src.main.get_config")
    @patch("src.main.RepositoryExtractor")
    def test_main_unexpected_error(self, mock_repo_ext, mock_get_config):
        """Test main handles unexpected errors."""
        # Setup config
        mock_config = Mock()
        mock_config.GITHUB_TOKEN = None
        mock_config.DEBUG_MODE = False
        mock_get_config.return_value = mock_config

        # Setup extractor to raise unexpected error
        mock_repo_ext.return_value.extract.side_effect = RuntimeError("Unexpected error")

        # Execute main
        result = main()

        # Verify error handling
        assert result == 1

    @patch("src.main.get_config")
    @patch("src.main.GitHubAPI")
    def test_main_github_api_initialization_failure(self, mock_github_api, mock_get_config):
        """Test main continues when GitHub API fails to initialize."""
        # Setup config
        mock_config = Mock()
        mock_config.GITHUB_TOKEN = "test-token"
        mock_config.DEBUG_MODE = False
        mock_get_config.return_value = mock_config

        # Setup GitHub API to raise error
        mock_github_api.side_effect = Exception("API initialization failed")

        # This should not prevent main from continuing
        # Main should catch the exception and continue without API
        # The test will fail later when trying to extract, which returns error code 1
        result = main()

        # Should return error code but not crash
        assert result == 1

    @patch("src.main.get_config")
    @patch("src.main.GitHubAPI")
    @patch("src.main.GitOperations")
    @patch("src.main.RepositoryExtractor")
    @patch("src.main.EventExtractor")
    @patch("src.main.RefExtractor")
    @patch("src.main.CommitExtractor")
    @patch("src.main.PullRequestExtractor")
    @patch("src.main.ActorExtractor")
    @patch("src.main.CacheExtractor")
    @patch("src.main.ChangedFilesExtractor")
    @patch("src.main.GerritExtractor")
    @patch("src.main.write_github_output")
    def test_main_without_github_token(
        self,
        mock_write_output,
        mock_gerrit_ext,
        mock_changed_ext,
        mock_cache_ext,
        mock_actor_ext,
        mock_pr_ext,
        mock_commit_ext,
        mock_ref_ext,
        mock_event_ext,
        mock_repo_ext,
        mock_git_ops,
        mock_github_api,
        mock_get_config,
        sample_metadata,
    ):
        """Test main execution without GitHub token."""
        # Setup config
        mock_config = Mock()
        mock_config.GITHUB_TOKEN = None  # No token
        mock_config.GITHUB_TOKEN = None
        mock_config.DEBUG_MODE = False
        mock_config.GITHUB_OUTPUT = Path("/tmp/output")
        mock_config.GITHUB_SUMMARY = False
        mock_config.GITHUB_STEP_SUMMARY = None
        mock_config.GERRIT_SUMMARY = False
        mock_config.GERRIT_INCLUDE_COMMENT = False
        mock_config.ARTIFACT_UPLOAD = False
        mock_get_config.return_value = mock_config

        # Setup git operations
        mock_git = Mock()
        mock_git.has_git_repo.return_value = False  # No git repo
        mock_git_ops.return_value = mock_git

        # Setup extractors
        mock_repo_ext.return_value.extract.return_value = sample_metadata.repository
        mock_event_ext.return_value.extract.return_value = sample_metadata.event
        mock_ref_ext.return_value.extract.return_value = sample_metadata.ref
        mock_commit_ext.return_value.extract.return_value = sample_metadata.commit
        mock_pr_ext.return_value.extract.return_value = sample_metadata.pull_request
        mock_actor_ext.return_value.extract.return_value = sample_metadata.actor
        mock_cache_ext.return_value.extract.return_value = sample_metadata.cache
        mock_changed_ext.return_value.extract.return_value = sample_metadata.changed_files
        mock_gerrit_ext.return_value.extract.return_value = sample_metadata.gerrit_environment

        # Execute main
        result = main()

        # Verify success even without token
        assert result == 0
        # GitHub API should not be initialized
        assert not mock_github_api.called


class TestMainLastCommitFiles:
    """Tests for last commit files integration in main()."""

    @patch("src.main.GerritExtractor")
    @patch("src.main.ChangedFilesLastCommitExtractor")
    @patch("src.main.ChangedFilesExtractor")
    @patch("src.main.CacheExtractor")
    @patch("src.main.ActorExtractor")
    @patch("src.main.PullRequestExtractor")
    @patch("src.main.CommitExtractor")
    @patch("src.main.RefExtractor")
    @patch("src.main.EventExtractor")
    @patch("src.main.RepositoryExtractor")
    @patch("src.main.GitOperations")
    @patch("src.main.get_config")
    @patch("builtins.open", create=True)
    def test_main_with_last_commit_files_summary(
        self,
        mock_open_func,
        mock_get_config,
        mock_git_ops,
        mock_repo_ext,
        mock_event_ext,
        mock_ref_ext,
        mock_commit_ext,
        mock_pr_ext,
        mock_actor_ext,
        mock_cache_ext,
        mock_changed_ext,
        mock_last_commit_ext,
        mock_gerrit_ext,
        sample_metadata_with_gerrit,
    ):
        """Test main() generates last commit files summary when Gerrit data present."""
        # Configure mocks
        mock_config = Mock()
        mock_config.DEBUG_MODE = False
        mock_config.GITHUB_TOKEN = None
        mock_config.GITHUB_OUTPUT = Path("/tmp/output")
        mock_config.GITHUB_SUMMARY = False
        mock_config.GITHUB_STEP_SUMMARY = Path("/tmp/summary")
        mock_config.GERRIT_SUMMARY = True  # Enable Gerrit summary
        mock_config.FILES_SUMMARY = False
        mock_config.GERRIT_INCLUDE_COMMENT = False
        mock_config.ARTIFACT_UPLOAD = False
        mock_get_config.return_value = mock_config

        # Setup git operations
        mock_git = Mock()
        mock_git.has_git_repo.return_value = True
        mock_git_ops.return_value = mock_git

        # Create metadata with last commit files
        metadata_with_files = sample_metadata_with_gerrit
        metadata_with_files.changed_files_last_commit = ChangedFilesMetadata(
            files=["README.md", "test.txt"],
            added=["test.txt"],
            modified=["README.md"],
        )

        # Setup extractors
        mock_repo_ext.return_value.extract.return_value = metadata_with_files.repository
        mock_event_ext.return_value.extract.return_value = metadata_with_files.event
        mock_ref_ext.return_value.extract.return_value = metadata_with_files.ref
        mock_commit_ext.return_value.extract.return_value = metadata_with_files.commit
        mock_pr_ext.return_value.extract.return_value = metadata_with_files.pull_request
        mock_actor_ext.return_value.extract.return_value = metadata_with_files.actor
        mock_cache_ext.return_value.extract.return_value = metadata_with_files.cache
        mock_changed_ext.return_value.extract.return_value = metadata_with_files.changed_files
        mock_last_commit_ext.return_value.extract.return_value = (
            metadata_with_files.changed_files_last_commit
        )
        mock_gerrit_ext.return_value.extract.return_value = metadata_with_files.gerrit_environment

        # Mock file operations
        mock_file = Mock()
        mock_open_func.return_value.__enter__.return_value = mock_file

        # Execute main
        result = main()

        # Verify success
        assert result == 0

        # Verify last commit extractor was called
        mock_last_commit_ext.assert_called_once()

        # Verify step summary was written (should include last commit files section)
        assert mock_file.write.called
        # Check that markdown content was written
        calls = [str(call) for call in mock_file.write.call_args_list]

        # Gerrit summary should be present
        assert any("Gerrit Parameters" in str(call) for call in calls)

    @patch("src.main.GerritExtractor")
    @patch("src.main.ChangedFilesLastCommitExtractor")
    @patch("src.main.ChangedFilesExtractor")
    @patch("src.main.CacheExtractor")
    @patch("src.main.ActorExtractor")
    @patch("src.main.PullRequestExtractor")
    @patch("src.main.CommitExtractor")
    @patch("src.main.RefExtractor")
    @patch("src.main.EventExtractor")
    @patch("src.main.RepositoryExtractor")
    @patch("src.main.GitOperations")
    @patch("src.main.get_config")
    @patch("builtins.open", create=True)
    def test_main_no_last_commit_summary_without_gerrit(
        self,
        mock_open_func,
        mock_get_config,
        mock_git_ops,
        mock_repo_ext,
        mock_event_ext,
        mock_ref_ext,
        mock_commit_ext,
        mock_pr_ext,
        mock_actor_ext,
        mock_cache_ext,
        mock_changed_ext,
        mock_last_commit_ext,
        mock_gerrit_ext,
        sample_metadata,
    ):
        """Test that last commit summary is NOT shown without Gerrit data."""
        # Configure mocks
        mock_config = Mock()
        mock_config.DEBUG_MODE = False
        mock_config.GITHUB_TOKEN = None
        mock_config.GITHUB_OUTPUT = Path("/tmp/output")
        mock_config.GITHUB_SUMMARY = False
        mock_config.GITHUB_STEP_SUMMARY = Path("/tmp/summary")
        mock_config.GERRIT_SUMMARY = True  # Enable Gerrit summary
        mock_config.FILES_SUMMARY = False
        mock_config.GERRIT_INCLUDE_COMMENT = False
        mock_config.ARTIFACT_UPLOAD = False
        mock_get_config.return_value = mock_config

        # Setup git operations
        mock_git = Mock()
        mock_git.has_git_repo.return_value = True
        mock_git_ops.return_value = mock_git

        # Create metadata with last commit files but NO Gerrit data
        metadata_no_gerrit = sample_metadata
        metadata_no_gerrit.changed_files_last_commit = ChangedFilesMetadata(
            files=["README.md"],
            modified=["README.md"],
        )

        # Setup extractors
        mock_repo_ext.return_value.extract.return_value = metadata_no_gerrit.repository
        mock_event_ext.return_value.extract.return_value = metadata_no_gerrit.event
        mock_ref_ext.return_value.extract.return_value = metadata_no_gerrit.ref
        mock_commit_ext.return_value.extract.return_value = metadata_no_gerrit.commit
        mock_pr_ext.return_value.extract.return_value = metadata_no_gerrit.pull_request
        mock_actor_ext.return_value.extract.return_value = metadata_no_gerrit.actor
        mock_cache_ext.return_value.extract.return_value = metadata_no_gerrit.cache
        mock_changed_ext.return_value.extract.return_value = metadata_no_gerrit.changed_files
        mock_last_commit_ext.return_value.extract.return_value = (
            metadata_no_gerrit.changed_files_last_commit
        )
        mock_gerrit_ext.return_value.extract.return_value = metadata_no_gerrit.gerrit_environment

        # Mock file operations
        mock_file = Mock()
        mock_open_func.return_value.__enter__.return_value = mock_file

        # Execute main
        result = main()

        # Verify success
        assert result == 0

        # Verify step summary does NOT include last commit files section
        calls = [str(call) for call in mock_file.write.call_args_list]

        # Last commit files section should NOT be present (no Gerrit change_id)
        assert not any("Changed Files (Last Commit)" in str(call) for call in calls)
