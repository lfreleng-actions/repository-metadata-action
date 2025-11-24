<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# 🛠️ Repository Metadata

Gathers comprehensive metadata about the GitHub repository, including
repository information, commit details, branch/tag information, pull request
context, event detection, and more for use in other actions and workflows.

## repository-metadata-action

This action provides a rich set of metadata outputs to help you make
intelligent decisions in your GitHub Actions workflows. It automatically
detects which event triggered the workflow and extracts relevant
information.

## Features

- 📦 **Repository Information**: Owner, name, visibility
- 🔀 **Branch/Tag Detection**: Identify branches, tags, and default branch
- 📝 **Commit Metadata**: SHA, message, author
- 🔄 **Pull Request Context**: PR number, source/target branches, fork
  detection
- 🎯 **Event Type Detection**: Automatically detect push, PR, release,
  schedule, etc.
- 🔑 **Cache Key Generation**: Smart cache keys for workflow optimization
- 📄 **Changed Files**: List of files changed in PRs and pushes
- 📋 **JSON Output**: All metadata in a single JSON object
- 📄 **YAML Output**: All metadata in YAML format
- 🔍 **Debug Mode**: Verbose logging for troubleshooting

## Usage Example

```yaml
steps:
    - name: "Checkout repository"
      uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Required for changed files detection

    - name: "Repository metadata"
      id: repository-metadata
      uses: lfreleng-actions/repository-metadata-action@main
      with:
        debug: false  # Set to true for verbose output
        github_token: ${{ secrets.GITHUB_TOKEN }}  # For changed files

    - name: "Use metadata"
      run: |
        echo "Repo: ${{ steps.repository-metadata.outputs.repository_full_name }}"
        echo "Branch: ${{ steps.repository-metadata.outputs.branch_name }}"
        echo "Commit: ${{ steps.repository-metadata.outputs.commit_sha_short }}"
        echo "Is PR: ${{ steps.repository-metadata.outputs.is_pull_request }}"
        echo "Cache: ${{ steps.repository-metadata.outputs.cache_key }}"
```

## Inputs

<!-- markdownlint-disable MD013 -->

| Variable Name    | Description                                            | Required | Default             |
| ---------------- | ------------------------------------------------------ | -------- | ------------------- |
| debug            | Enable debug mode for verbose output                   | No       | false               |
| github_token     | GitHub token for API access (changed files)            | No       | ${{ github.token }} |
| generate_summary | Generate summary in GITHUB_STEP_SUMMARY                | No       | false               |
| artifact_upload  | Upload metadata as workflow artifact                   | No       | true                |
| artifact_formats | Comma-separated list of formats to upload (json, yaml) | No       | json,yaml           |
| change_detection | Changed files detection method: 'git' or 'github_api'  | No       | (auto)              |
| git_fetch_depth  | Depth for git fetch --deepen in shallow clones         | No       | 15                  |

<!-- markdownlint-enable MD013 -->

## Outputs

### Repository Outputs

<!-- markdownlint-disable MD013 -->

| Variable Name          | Description                                    |
| ---------------------- | ---------------------------------------------- |
| repository_owner       | Name of the GitHub organization                |
| repository_name        | Name of the GitHub repository                  |
| repository_full_name   | Full repository name (owner/name)              |
| is_public              | Returns true if the repository is public       |
| is_private             | Returns true if the repository is private      |

<!-- markdownlint-enable MD013 -->

### Event Type Detection Outputs

<!-- markdownlint-disable MD013 -->

| Variable Name        | Description                                            |
| -------------------- | ------------------------------------------------------ |
| event_name           | The name of the event that triggered the workflow      |
| tag_push_event       | Returns true if a version tag push triggered the event |
| is_tag_push          | Returns true if the event is a tag push                |
| is_branch_push       | Returns true if the event is a branch push             |
| is_pull_request      | Returns true if the event is a pull request            |
| is_release           | Returns true if the event is a release                 |
| is_schedule          | Returns true if the event runs on a schedule           |
| is_workflow_dispatch | Returns true if the event is manually triggered        |

<!-- markdownlint-enable MD013 -->

### Branch and Tag Outputs

<!-- markdownlint-disable MD013 -->

| Variable Name      | Description                                         |
| ------------------ | --------------------------------------------------- |
| branch_name        | Returns the branch name (empty for tag pushes)      |
| tag_name           | Returns the tag name (empty if not a tag)           |
| is_default_branch  | Returns true if running on the default branch       |
| is_main_branch     | Returns true if running on main or master branch    |

<!-- markdownlint-enable MD013 -->

### Commit Outputs

<!-- markdownlint-disable MD013 -->

| Variable Name     | Description                              |
| ----------------- | ---------------------------------------- |
| commit_sha        | Full commit SHA                          |
| commit_sha_short  | Short commit SHA (first 7 characters)    |
| commit_message    | Commit message title                     |
| commit_author     | Commit author name                       |

<!-- markdownlint-enable MD013 -->

### Pull Request Outputs

<!-- markdownlint-disable MD013 -->

| Variable Name      | Description                                       |
| ------------------ | ------------------------------------------------- |
| pr_number          | Pull request number (empty if not a PR)           |
| pr_source_branch   | Pull request source branch (head ref)             |
| pr_target_branch   | Pull request target branch (base ref)             |
| is_fork            | Returns true if pull request is from a fork       |
| pr_commits_count   | Number of commits in the pull request             |

<!-- markdownlint-enable MD013 -->

### Actor Outputs

<!-- markdownlint-disable MD013 -->

| Variable Name | Description                                    |
| ------------- | ---------------------------------------------- |
| actor         | GitHub actor (user who triggered the workflow) |
| actor_id      | GitHub actor ID                                |

<!-- markdownlint-enable MD013 -->

### Cache Outputs

<!-- markdownlint-disable MD013 -->

| Variable Name     | Description                                        |
| ----------------- | -------------------------------------------------- |
| cache_key         | Generated cache key based on repository and commit |
| cache_restore_key | Generated cache restore key prefix                 |

<!-- markdownlint-enable MD013 -->

### Changed Files Outputs

<!-- markdownlint-disable MD013 -->

| Variable Name       | Description                                      |
| ------------------- | ------------------------------------------------ |
| changed_files       | List of changed files (space-separated)          |
| changed_files_count | Number of changed files                          |

<!-- markdownlint-enable MD013 -->

### Artifact Outputs

<!-- markdownlint-disable MD013 -->

| Variable Name   | Description                                                |
| --------------- | ---------------------------------------------------------- |
| artifact_path   | Path to the metadata artifact files (if uploaded)          |
| artifact_suffix | Unique 4-character alphanumeric suffix for artifact naming |

<!-- markdownlint-enable MD013 -->

**Note**: Changed files detection requires checking out the repository
with git history. For pull requests, it works best with the `github_token`
input provided.

### JSON and YAML Outputs

<!-- markdownlint-disable MD013 -->

| Variable Name | Description                        |
| ------------- | ---------------------------------- |
| metadata_json | All metadata as a JSON object      |
| metadata_yaml | All metadata as a YAML object      |

<!-- markdownlint-enable MD013 -->

Both JSON and YAML outputs contain all metadata in structured formats:

**JSON Format:**

```json
{
  "repository": {
    "owner": "owner-name",
    "name": "repo-name",
    "full_name": "owner-name/repo-name",
    "is_public": true,
    "is_private": false
  },
  "event": {
    "name": "push",
    "is_tag_push": false,
    "is_branch_push": true,
    "is_pull_request": false,
    "is_release": false,
    "is_schedule": false,
    "is_workflow_dispatch": false,
    "tag_push_event": false
  },
  "ref": {
    "branch_name": "main",
    "tag_name": "",
    "is_default_branch": true,
    "is_main_branch": true
  },
  "commit": {
    "sha": "abc123...",
    "sha_short": "abc123",
    "message": "Commit message",
    "author": "Author Name"
  },
  "pull_request": {
    "number": "",
    "source_branch": "",
    "target_branch": "",
    "is_fork": false
  },
  "actor": {
    "name": "username",
    "id": "12345"
  },
  "cache": {
    "key": "owner-repo-main-abc123",
    "restore_key": "owner-repo-main-"
  },
  "changed_files": {
    "count": 0,
    "files": ""
  }
}
```

**YAML Format:**

```yaml
repository:
  owner: owner-name
  name: repo-name
  full_name: owner-name/repo-name
  is_public: true
  is_private: false
event:
  name: push
  is_tag_push: false
  is_branch_push: true
  is_pull_request: false
  is_release: false
  is_schedule: false
  is_workflow_dispatch: false
  tag_push_event: false
ref:
  branch_name: main
  tag_name: ""
  is_default_branch: true
  is_main_branch: true
commit:
  sha: abc123...
  sha_short: abc123
  message: Commit message
  author: Author Name
pull_request:
  number: null
  source_branch: ""
  target_branch: ""
  is_fork: false
actor:
  name: username
  id: 12345
cache:
  key: owner-repo-main-abc123
  restore_key: owner-repo-main-
changed_files:
  count: 0
  files: ""
```

## Artifact Upload

By default, the action uploads metadata as a workflow artifact. Each invocation
generates a unique artifact name to avoid conflicts when calling the action
more than once in the same workflow.

**Artifact Naming Format**: `repository-metadata-<job-name>-<suffix>`

Where `<suffix>` is a randomly generated 4-character alphanumeric string
(e.g., `a3f9`, `x2k5`).

**Examples**:

- `repository-metadata-tests-a3f9`
- `repository-metadata-build-x2k5`
- `repository-metadata-deploy-7n4m`

The artifact contains (by default):

- `metadata.json` - Compact JSON format
- `metadata-pretty.json` - Pretty-printed JSON for human readability
- `metadata.yaml` - YAML format

**Customize artifact formats:**

```yaml
# Upload JSON format
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    artifact_formats: json

# Upload YAML format
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    artifact_formats: yaml

# Upload both (default)
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    artifact_formats: json,yaml
```

**Disable artifact upload:**

```yaml
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    artifact_upload: false
```

## Changed Files Detection

The action supports two methods for detecting changed files in pull requests:

### Automatic (Default)

When you provide `github_token`, the action uses the GitHub API. Otherwise,
it falls back to git-based detection.

### Explicit Method Selection

You can force a specific detection method using the `change_detection` input:

**Git-based detection** (works offline, requires git history):

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0  # Required for git-based detection

- uses: lfreleng-actions/repository-metadata-action@main
  with:
    change_detection: git
```

**GitHub API-based detection** (requires token):

```yaml
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    change_detection: github_api
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

The action automatically handles shallow clones by fetching the base branch
when needed for accurate file change detection.

### Git Fetch Depth Configuration

When using git-based detection with shallow clones, the action may need to
fetch more history to find the common ancestor between the PR branch
and the base branch. You can configure the fetch depth:

```yaml
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    change_detection: git
    git_fetch_depth: 15  # Default: 15 commits
```

**When to adjust**:

- **Increase** (e.g., 30-50) if you have PRs with more than 15 commits
- **Decrease** (e.g., 5-10) for faster fetches if PRs are typically small
- Most PRs have fewer than 15 commits, making the default appropriate for
  most use cases

## Advanced Examples

### Conditional Job Execution Based on Event Type

```yaml
jobs:
  metadata:
    runs-on: ubuntu-latest
    outputs:
      is_release: ${{ steps.meta.outputs.is_release }}
      is_main_branch: ${{ steps.meta.outputs.is_main_branch }}
    steps:
      - uses: actions/checkout@v4
      - id: meta
        uses: lfreleng-actions/repository-metadata-action@main

  deploy:
    needs: metadata
    if: needs.metadata.outputs.is_release == 'true'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploying release..."

  build:
    needs: metadata
    if: needs.metadata.outputs.is_main_branch == 'true'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Building from main branch..."
```

### Using Cache Keys

```yaml
steps:
  - uses: actions/checkout@v4

  - id: metadata
    uses: lfreleng-actions/repository-metadata-action@main

  - uses: actions/cache@v4
    with:
      path: ~/.cache/pip
      key: ${{ steps.metadata.outputs.cache_key }}-pip
      restore-keys: |
        ${{ steps.metadata.outputs.cache_restore_key }}-pip
```

### Processing Changed Files

```yaml
steps:
  - uses: actions/checkout@v4
    with:
      fetch-depth: 0

  - id: metadata
    uses: lfreleng-actions/repository-metadata-action@main
    with:
      github_token: ${{ secrets.GITHUB_TOKEN }}

  - name: "Check if docs changed"
    if: steps.metadata.outputs.is_pull_request == 'true'
    run: |
      changed="${{ steps.metadata.outputs.changed_files }}"
      if echo "$changed" | grep -q "docs/"; then
        echo "This PR modifies documentation files"
      fi

  - name: "Check PR commit count"
    if: steps.metadata.outputs.is_pull_request == 'true'
    run: |
      commit_count="${{ steps.metadata.outputs.pr_commits_count }}"
      if [ "$commit_count" -gt 10 ]; then
        echo "⚠️ This PR has $commit_count commits - consider squashing"
      else
        echo "✅ This PR has $commit_count commits"
      fi
```

### Using JSON Output for Complex Logic

```yaml
steps:
  - uses: actions/checkout@v4

  - id: metadata
    uses: lfreleng-actions/repository-metadata-action@main

  - name: "Process metadata with jq"
    env:
      METADATA: ${{ steps.metadata.outputs.metadata_json }}
    run: |
      echo "$METADATA" | jq '.repository.owner'
      echo "$METADATA" | jq '.commit.sha_short'
      echo "$METADATA" | jq '.event | to_entries[] | select(.value == true)'
```

### Using YAML Output

```yaml
steps:
  - uses: actions/checkout@v4

  - id: metadata
    uses: lfreleng-actions/repository-metadata-action@main

  - name: "Process metadata with yq"
    env:
      METADATA: ${{ steps.metadata.outputs.metadata_yaml }}
    run: |
      echo "$METADATA" | yq eval '.repository.owner'
      echo "$METADATA" | yq eval '.commit.sha_short'
      echo "$METADATA" | yq eval '.ref.branch_name'
```

### Debug Mode

Enable debug mode to see detailed information about the metadata extraction:

```yaml
steps:
  - id: metadata
    uses: lfreleng-actions/repository-metadata-action@main
    with:
      debug: true
```

## Notes

- The action uses `set -euo pipefail` for robust error handling
- For pull requests, changed files detection works best when you check out
  the repository with full git history (`fetch-depth: 0`)
- The `tag_push_event` output specifically detects version tags that start
  with 'v' followed by numbers (e.g., v1.0.0, v2.1.3)
- Repository visibility detection requires the `GITHUB_REPOSITORY_VISIBILITY`
  environment variable, which may not be available in all contexts
- The `github_token` input is optional but recommended for pull request
  changed files detection

## License

Apache-2.0

## Contributing

Contributions are welcome! Please ensure all changes pass the pre-commit
hooks and tests.
