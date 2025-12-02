# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""
Tests for Pydantic data models.
"""

import pytest

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


class TestRepositoryMetadata:
    """Tests for RepositoryMetadata model."""

    def test_basic_creation(self):
        """Test basic repository metadata creation."""
        repo = RepositoryMetadata(
            owner="testowner",
            name="testrepo",
            full_name="testowner/testrepo",
            is_public=True,
            is_private=False,
        )

        assert repo.owner == "testowner"
        assert repo.name == "testrepo"
        assert repo.full_name == "testowner/testrepo"
        assert repo.is_public is True
        assert repo.is_private is False

    def test_visibility_mutual_exclusion(self):
        """Test that repository cannot be both public and private."""
        with pytest.raises(ValueError, match="cannot be both public and private"):
            RepositoryMetadata(
                owner="testowner",
                name="testrepo",
                full_name="testowner/testrepo",
                is_public=True,
                is_private=True,
            )


class TestCommitMetadata:
    """Tests for CommitMetadata model."""

    def test_short_sha_auto_generation(self):
        """Test that short SHA is auto-generated from full SHA."""
        commit = CommitMetadata(sha="abc123def456789012345678901234567890abcd", sha_short="")

        assert commit.sha_short == "abc123d"

    def test_short_sha_validation(self):
        """Test that short SHA must be 7 characters."""
        with pytest.raises(ValueError, match="must be 7 characters"):
            CommitMetadata(sha="abc123def456789012345678901234567890abcd", sha_short="abc")

    def test_with_message_and_author(self):
        """Test commit with message and author."""
        commit = CommitMetadata(
            sha="abc123def456789012345678901234567890abcd",
            sha_short="abc123d",
            message="Test commit message",
            author="Test Author",
        )

        assert commit.message == "Test commit message"
        assert commit.author == "Test Author"


class TestChangedFilesMetadata:
    """Tests for ChangedFilesMetadata model."""

    def test_count_auto_sync(self):
        """Test that count automatically syncs with files list."""
        files = ChangedFilesMetadata(files=["file1.py", "file2.py", "file3.py"])

        assert files.count == 3

    def test_empty_files(self):
        """Test empty files list."""
        files = ChangedFilesMetadata()

        assert files.count == 0
        assert files.files == []


class TestCompleteMetadata:
    """Tests for CompleteMetadata model."""

    def test_complete_metadata_creation(self):
        """Test creating complete metadata with all components."""
        metadata = CompleteMetadata(
            repository=RepositoryMetadata(
                owner="owner", name="repo", full_name="owner/repo", is_public=True
            ),
            event=EventMetadata(name="push", is_branch_push=True),
            ref=RefMetadata(branch_name="main", is_main_branch=True),
            commit=CommitMetadata(
                sha="abc123def456789012345678901234567890abcd", sha_short="abc123d"
            ),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="testuser", id=12345),
            cache=CacheMetadata(key="test-cache-key", restore_key="test-cache-"),
            changed_files=ChangedFilesMetadata(files=["file1.py"]),
            changed_files_last_commit=ChangedFilesMetadata(files=["file1.py"]),
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

        assert metadata.repository.owner == "owner"
        assert metadata.event.name == "push"
        assert metadata.ref.branch_name == "main"
        assert metadata.commit.sha_short == "abc123d"
        assert metadata.actor.name == "testuser"
        assert metadata.changed_files.count == 1

    def test_to_action_outputs(self):
        """Test conversion to GitHub Action outputs format."""
        metadata = CompleteMetadata(
            repository=RepositoryMetadata(
                owner="owner", name="repo", full_name="owner/repo", is_public=True
            ),
            event=EventMetadata(name="push", is_branch_push=True),
            ref=RefMetadata(branch_name="main"),
            commit=CommitMetadata(
                sha="abc123def456789012345678901234567890abcd", sha_short="abc123d"
            ),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="testuser"),
            cache=CacheMetadata(key="test-key", restore_key="test-"),
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

        outputs = metadata.to_action_outputs()

        # Check all required outputs are present
        assert outputs["repository_owner"] == "owner"
        assert outputs["repository_name"] == "repo"
        assert outputs["repository_full_name"] == "owner/repo"
        assert outputs["is_public"] == "true"
        assert outputs["is_private"] == "false"
        assert outputs["event_name"] == "push"
        assert outputs["is_branch_push"] == "true"
        assert outputs["branch_name"] == "main"
        assert outputs["commit_sha"] == "abc123def456789012345678901234567890abcd"
        assert outputs["commit_sha_short"] == "abc123d"
        assert outputs["actor"] == "testuser"
        assert outputs["cache_key"] == "test-key"
        assert outputs["changed_files_count"] == "0"
        assert outputs["changed_files_last_commit_count"] == "0"

    def test_to_json(self):
        """Test JSON serialization."""
        metadata = CompleteMetadata(
            repository=RepositoryMetadata(owner="owner", name="repo", full_name="owner/repo"),
            event=EventMetadata(name="push"),
            ref=RefMetadata(),
            commit=CommitMetadata(
                sha="abc123def456789012345678901234567890abcd", sha_short="abc123d"
            ),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="testuser"),
            cache=CacheMetadata(key="key", restore_key="restore"),
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

        json_str = metadata.to_json()
        assert isinstance(json_str, str)
        assert "owner" in json_str
        assert "push" in json_str

    def test_with_gerrit_metadata(self):
        """Test complete metadata with Gerrit data."""
        metadata = CompleteMetadata(
            repository=RepositoryMetadata(owner="owner", name="repo", full_name="owner/repo"),
            event=EventMetadata(name="workflow_dispatch", is_workflow_dispatch=True),
            ref=RefMetadata(branch_name="main"),
            commit=CommitMetadata(
                sha="abc123def456789012345678901234567890abcd", sha_short="abc123d"
            ),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="testuser"),
            cache=CacheMetadata(key="key", restore_key="restore"),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(),
            gerrit_environment=GerritMetadata(
                branch="main", change_id="I1234567890abcdef", change_number="12345"
            ),
        )

        assert metadata.gerrit_environment is not None
        assert metadata.gerrit_environment.change_id == "I1234567890abcdef"

        outputs = metadata.to_action_outputs()
        assert outputs["gerrit_json"] != ""
        assert "I1234567890abcdef" in outputs["gerrit_json"]

    def test_changed_files_last_commit_outputs(self):
        """Test that changed_files_last_commit outputs are included."""
        metadata = CompleteMetadata(
            repository=RepositoryMetadata(owner="owner", name="repo", full_name="owner/repo"),
            event=EventMetadata(name="workflow_dispatch", is_workflow_dispatch=True),
            ref=RefMetadata(branch_name="main"),
            commit=CommitMetadata(
                sha="abc123def456789012345678901234567890abcd", sha_short="abc123d"
            ),
            pull_request=PullRequestMetadata(),
            actor=ActorMetadata(name="testuser"),
            cache=CacheMetadata(key="key", restore_key="restore"),
            changed_files=ChangedFilesMetadata(),
            changed_files_last_commit=ChangedFilesMetadata(
                files=["file1.py", "file2.py"],
                added=["file1.py"],
                modified=["file2.py"],
                removed=[],
            ),
            gerrit_environment=GerritMetadata(
                branch="main", change_id="I1234567890abcdef", change_number="12345"
            ),
        )

        outputs = metadata.to_action_outputs()

        # Verify last commit outputs are present
        assert "changed_files_last_commit" in outputs
        assert "changed_files_last_commit_count" in outputs
        assert "changed_files_last_commit_added" in outputs
        assert "changed_files_last_commit_added_count" in outputs
        assert "changed_files_last_commit_modified" in outputs
        assert "changed_files_last_commit_modified_count" in outputs
        assert "changed_files_last_commit_removed" in outputs
        assert "changed_files_last_commit_removed_count" in outputs

        # Verify values
        assert outputs["changed_files_last_commit_count"] == "2"
        assert outputs["changed_files_last_commit_added_count"] == "1"
        assert outputs["changed_files_last_commit_modified_count"] == "1"
        assert outputs["changed_files_last_commit_removed_count"] == "0"
        assert "file1.py" in outputs["changed_files_last_commit"]
        assert "file2.py" in outputs["changed_files_last_commit"]
