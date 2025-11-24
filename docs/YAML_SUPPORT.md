<!--
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# YAML Output Support - Repository Metadata Action

## Overview

The `repository-metadata-action` now supports both JSON and YAML output
formats, providing flexibility for downstream consumers and maintaining
consistency with the `build-metadata-action`. Both formats contain identical
metadata generated from the same source data.

## Key Features

- ✅ **Dual Format Support**: JSON and YAML outputs available simultaneously
- 🔄 **Data Consistency**: Both formats contain identical metadata
- 📦 **Flexible Artifacts**: Control which formats to upload via
  `artifact_formats` input
- 🛠️ **Tool Compatibility**: Works with `jq` (JSON) and `yq` (YAML)
- ⚡ **Zero Configuration**: YAML enabled by default, no setup required
- 🔒 **Mandatory Generation**: Both formats always generated (fail-safe
  design)

## Why YAML?

### Use Cases for YAML Output

1. **Human Readability**: YAML is more readable in code reviews and
   documentation
2. **Tool Preference**: Some CI/CD tools prefer YAML configuration
3. **Consistency**: Matches `build-metadata-action` interface pattern
4. **Downstream Integration**: Easier integration with YAML-based systems
5. **Template Engines**: Better for tools like Helm, Ansible, or Jinja2

### JSON vs YAML

| Feature            | JSON             | YAML                |
| ------------------ | ---------------- | ------------------- |
| **Compactness**    | ✅ More compact   | ❌ More verbose      |
| **Readability**    | ❌ Less readable  | ✅ More readable     |
| **Parsing Speed**  | ✅ Faster         | ❌ Slower            |
| **Comments**       | ❌ No support     | ✅ Supports comments |
| **GitHub Actions** | ✅ Native support | ⚠️ Needs `yq`       |
| **Best For**       | Automation, APIs | Humans, configs     |

**Recommendation**: Use JSON for automation, YAML for human review and
debugging.

## Quick Start

### Access YAML Output

```yaml
steps:
  - name: "Repository metadata"
    id: metadata
    uses: lfreleng-actions/repository-metadata-action@main

  - name: "Use YAML output"
    run: |
        BRANCH=$(echo '${{ steps.metadata.outputs.metadata_yaml }}' \
          | yq eval '.ref.branch_name' -)
        COMMIT=$(echo '${{ steps.metadata.outputs.metadata_yaml }}' \
          | yq eval '.commit.sha_short' -)
        echo "Branch: $BRANCH"
        echo "Commit: $COMMIT"
```

### Access Both Formats

```yaml
steps:
  - name: "Repository metadata"
    id: metadata
    uses: lfreleng-actions/repository-metadata-action@main

  - name: "Use JSON for automation"
    env:
      METADATA: ${{ steps.metadata.outputs.metadata_json }}
    run: |
      VERSION=$(echo "$METADATA" | jq -r '.commit.sha_short')
      docker build -t myapp:${VERSION} .

  - name: "Use YAML for reporting"
    env:
      METADATA: ${{ steps.metadata.outputs.metadata_yaml }}
    run: |
      echo "$METADATA" > metadata-report.yaml
      cat metadata-report.yaml  # More readable in logs
```

## Outputs

### metadata_yaml

**Type**: String (multi-line)

**Description**: Complete repository metadata in YAML format

**Example**:

```yaml
repository:
  owner: lfreleng-actions
  name: repository-metadata-action
  full_name: lfreleng-actions/repository-metadata-action
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
  sha: a1b2c3d4e5f6789012345678901234567890abcd
  sha_short: a1b2c3d
  message: "Add YAML support"
  author: "Developer Name"
pull_request:
  number: null
  source_branch: ""
  target_branch: ""
  is_fork: false
actor:
  name: developer
  id: 12345
cache:
  key: lfreleng-actions-repository-metadata-action-main-a1b2c3d
  restore_key: lfreleng-actions-repository-metadata-action-main-
changed_files:
  count: 3
  files: "action.yaml scripts/extract-metadata.sh README.md"
```

## Artifact Upload

### Default Behavior

By default, artifacts include both JSON and YAML formats:

```yaml
- uses: lfreleng-actions/repository-metadata-action@main
  # Creates artifact with:
  # - metadata.json (compact JSON)
  # - metadata-pretty.json (formatted JSON)
  # - metadata.yaml (YAML format)
```

### Customize Artifact Formats

Control which formats to include in artifacts using the `artifact_formats`
input:

#### JSON Format

```yaml
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    artifact_formats: json
  # Creates artifact with:
  # - metadata.json
  # - metadata-pretty.json
```

#### YAML Format

```yaml
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    artifact_formats: yaml
  # Creates artifact with:
  # - metadata.yaml
```

#### Both Formats (Default)

```yaml
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    artifact_formats: json,yaml
  # Creates artifact with:
  # - metadata.json
  # - metadata-pretty.json
  # - metadata.yaml
```

### Format Selection Use Cases

<!-- markdownlint-disable MD013 -->

| Scenario                 | Recommended Format | Rationale                       |
| ------------------------ | ------------------ | ------------------------------- |
| CI/CD automation         | `json`             | Faster parsing, more compact    |
| Documentation generation | `yaml`             | More readable in rendered docs  |
| Compliance/audit         | `json,yaml`        | Flexibility for different tools |
| Local development        | `yaml`             | Easier to read and debug        |
| API integration          | `json`             | Standard web API format         |
| Configuration management | `yaml`             | Ansible, Helm, etc. prefer YAML |

<!-- markdownlint-enable MD013 -->

## Processing YAML Output

### Using yq in GitHub Actions

```yaml
steps:
  - name: "Get metadata"
    id: metadata
    uses: lfreleng-actions/repository-metadata-action@main

  - name: "Extract specific fields"
    env:
      METADATA: ${{ steps.metadata.outputs.metadata_yaml }}
    run: |
      # Extract single values
      OWNER=$(echo "$METADATA" | yq eval '.repository.owner' -)
      BRANCH=$(echo "$METADATA" | yq eval '.ref.branch_name' -)
      SHA=$(echo "$METADATA" | yq eval '.commit.sha_short' -)

      echo "Building $OWNER from $BRANCH at $SHA"

      # Extract arrays/lists
      IS_PR=$(echo "$METADATA" | yq eval '.event.is_pull_request' -)

      if [ "$IS_PR" = "true" ]; then
        PR_NUM=$(echo "$METADATA" | yq eval '.pull_request.number' -)
        echo "Processing PR #$PR_NUM"
      fi
```

### Using yq in Download Artifact Workflow

```yaml
jobs:
  extract-metadata:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - id: metadata
        uses: lfreleng-actions/repository-metadata-action@main

  use-metadata:
    needs: extract-metadata
    runs-on: ubuntu-latest
    steps:
      - name: "Download metadata artifact"
        uses: actions/download-artifact@v4
        with:
          name: repository-metadata-${{ github.job }}-*
          path: ./metadata

      - name: "Process YAML artifact"
        run: |
          # Read from downloaded artifact
          REPO_OWNER=$(yq eval '.repository.owner' metadata/metadata.yaml)
          COMMIT_SHA=$(yq eval '.commit.sha' metadata/metadata.yaml)

          echo "Repository: $REPO_OWNER"
          echo "Commit: $COMMIT_SHA"

          # Convert YAML to JSON if needed
          yq eval -o=json metadata/metadata.yaml > metadata/converted.json

          # Query the converted JSON
          jq '.event.name' metadata/converted.json
```

### Complex yq Queries

```bash
# Get all event types that are true
echo "$METADATA" | \
  yq eval '.event | to_entries | .[] | select(.value == true) | .key' -

# Filter and transform
echo "$METADATA" | \
  yq eval '{owner: .repository.owner, branch: .ref.branch_name}' -

# Conditional logic
echo "$METADATA" | yq eval '
  if .event.is_pull_request then
    "PR from " + .pull_request.source_branch
  else
    "Push to " + .ref.branch_name
  end
' -

# Extract changed files as array
echo "$METADATA" | \
  yq eval '.changed_files.files | split(" ")' -
```

## Implementation Details

### How YAML Generation Works

1. **Source Data**: All metadata collected in bash variables
2. **JSON Generation**: Metadata assembled into JSON using `jq`
3. **YAML Conversion**: JSON converted to YAML using `yq -P` (preserves
   structure)
4. **Validation**: Both formats set as outputs (script fails if either fails)

### Why JSON → YAML Conversion?

**Advantages**:

- Single source of truth (JSON construction is well-tested)
- Guaranteed consistency between formats
- Leverages `jq`'s robust type handling
- `yq` handles all edge cases (escaping, special characters, etc.)

**Process**:

```bash
# 1. Build JSON with jq (lines 473-556)
METADATA_JSON=$(jq -nc --arg key "value" '{ "key": $key }')

# 2. Convert to YAML with yq (line 578)
METADATA_YAML=$(echo "${METADATA_JSON}" | yq -P .)

# 3. Both outputs set (fail if either fails due to set -euo pipefail)
set_output "metadata_json" "${METADATA_JSON}"
set_output "metadata_yaml" "${METADATA_YAML}"
```

### Error Handling

Both JSON and YAML generation use **strict error handling**:

```bash
set -euo pipefail
```

This means:

- ✅ If `jq` fails, script exits (no JSON or YAML output)
- ✅ If `yq` fails, script exits (no YAML output)
- ✅ No partial or corrupted output
- ✅ Action fails fast with clear error message

**Why mandatory instead of optional?**

- The action's purpose is to provide metadata
- Downstream consumers expect reliable output
- Making YAML optional creates inconsistent behavior
- If JSON succeeds, YAML should too (same data)

## Dependencies

### yq Availability

**GitHub-hosted runners**: `yq` is pre-installed on all GitHub-hosted
runners:

- ✅ ubuntu-latest
- ✅ ubuntu-22.04
- ✅ ubuntu-20.04
- ✅ macos-latest
- ✅ macos-13
- ✅ macos-12
- ✅ windows-latest

**Self-hosted runners**: Install `yq` if not available:

```yaml
- name: Install yq
  run: |
    YQ_URL="https://github.com/mikefarah/yq/releases/latest/download"
    sudo wget -qO /usr/local/bin/yq ${YQ_URL}/yq_linux_amd64
    sudo chmod +x /usr/local/bin/yq
```

Or use Docker:

```yaml
- uses: lfreleng-actions/repository-metadata-action@main
  # Run in container with yq pre-installed if needed
```

## Comparison with build-metadata-action

Both actions now follow the same pattern:

| Feature         | repository-metadata-action | build-metadata-action |
| --------------- | -------------------------- | --------------------- |
| JSON output     | ✅ `metadata_json`          | ✅ `metadata_json`     |
| YAML output     | ✅ `metadata_yaml`          | ✅ `metadata_yaml`     |
| Artifact upload | ✅ Configurable             | ✅ Configurable        |
| Format control  | ✅ `artifact_formats`       | ✅ `artifact_formats`  |
| Default formats | `json,yaml`                | `json,yaml`           |
| Validation      | ✅ Built-in (via tools)     | ✅ Explicit validation |
| Error handling  | ✅ Fail fast                | ✅ Fail fast           |

**Design Consistency**: Both actions share:

- Same input names (`artifact_formats`)
- Same output names (`metadata_json`, `metadata_yaml`)
- Same artifact file names (`metadata.json`, `metadata.yaml`, etc.)
- Same error handling philosophy

## Best Practices

### 1. Use JSON for Automation

```yaml
# Good: Fast parsing for CI/CD
- name: Build Docker image
  env:
    METADATA: ${{ steps.metadata.outputs.metadata_json }}
  run: |
    TAG=$(echo "$METADATA" | jq -r '.commit.sha_short')
    docker build -t myapp:$TAG .
```

### 2. Use YAML for Human Review

```yaml
# Good: Easy to read in PR comments
- name: Post metadata summary
  env:
    METADATA: ${{ steps.metadata.outputs.metadata_yaml }}
  run: |
    cat >> $GITHUB_STEP_SUMMARY << 'EOF'
    ## Metadata
    ```yaml
    ${{ steps.metadata.outputs.metadata_yaml }}
    ```
    EOF
```

### 3. Choose Appropriate Artifact Format

```yaml
# For automated pipelines
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    artifact_formats: json  # Smaller, faster

# For compliance/audit
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    artifact_formats: json,yaml  # Both for flexibility
```

### 4. Check Output Before Use

```yaml
- name: Check YAML output
  env:
    METADATA: ${{ steps.metadata.outputs.metadata_yaml }}
  run: |
    # Ensure valid YAML
    echo "$METADATA" | yq eval . > /dev/null || exit 1

    # Ensure required fields exist
    OWNER=$(echo "$METADATA" | yq eval '.repository.owner' -)
    [ -n "$OWNER" ] || { echo "Missing repository owner"; exit 1; }
```

### 5. Cache Processed Metadata

```yaml
- name: Process and cache metadata
  env:
    METADATA: ${{ steps.metadata.outputs.metadata_yaml }}
  run: |
    # Process once, cache results
    echo "$METADATA" > /tmp/metadata.yaml
    yq eval '.repository.owner' /tmp/metadata.yaml > /tmp/owner.txt
    yq eval '.commit.sha_short' /tmp/metadata.yaml > /tmp/sha.txt

- name: Use cached values
  run: |
    OWNER=$(cat /tmp/owner.txt)
    SHA=$(cat /tmp/sha.txt)
    echo "Building $OWNER at $SHA"
```

## Troubleshooting

### YAML Output is Empty

**Problem**: `metadata_yaml` output is empty

**Solution**:

```yaml
# Check debug mode
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    debug: true  # Shows YAML generation process

# Verify yq is available
- name: Check yq availability
  run: |
    which yq && yq --version  # Version 4 or higher required
```

### YAML Parsing Errors

**Problem**: The `yq eval` command fails with syntax error

**Cause**: Multi-line output requires proper handling

**Solution**:

```yaml
# Bad: Direct substitution in YAML
- run: echo ${{ steps.metadata.outputs.metadata_yaml }}

# Good: Use environment variable
- env:
    METADATA: ${{ steps.metadata.outputs.metadata_yaml }}
  run: echo "$METADATA" | yq eval '.repository.owner' -

# Good: Write to file first
- run: |
    echo '${{ steps.metadata.outputs.metadata_yaml }}' > metadata.yaml
    yq eval '.repository.owner' metadata.yaml
```

### Artifact Format Not Applied

**Problem**: Artifact contains unexpected files

**Cause**: Format string parsing issue

**Solution**:

```yaml
# Ensure no spaces in format list
- uses: lfreleng-actions/repository-metadata-action@main
  with:
    artifact_formats: json,yaml  # Correct

# Not this: artifact_formats: "json, yaml"  # Space causes issues
```

### yq Not Found (Self-hosted Runners)

**Problem**: `yq: command not found`

**Solution**:

```yaml
- name: Install yq
  run: |
    YQ_VERSION=v4.40.5
    YQ_URL="https://github.com/mikefarah/yq/releases/download"
    wget ${YQ_URL}/${YQ_VERSION}/yq_linux_amd64 -O /usr/local/bin/yq
    chmod +x /usr/local/bin/yq

- uses: lfreleng-actions/repository-metadata-action@main
```

## Future Enhancements

### Planned Features

1. **Format Validation**: Explicit validation step for both formats
2. **Schema Support**: JSON Schema and YAML schema validation
3. **More Formats**: XML, TOML support
4. **Compression**: Gzip compression for large metadata
5. **Streaming**: Stream processing for large outputs

### Feedback Welcome

Please open an issue or PR if you:

- Find bugs in YAML generation
- Have suggestions for improvements
- Need more output formats
- Want new artifact configuration options

## Related Documentation

- [Main README](../README.md)
- [Artifact Upload](../../build-metadata-action/docs/ARTIFACT_UPLOAD.md)
- [Build Metadata Action](../../build-metadata-action/README.md)

## Support

For YAML-related issues:

1. Enable debug mode with the input `debug: true`
2. Check the action logs for YAML generation output
3. Verify `yq` version: `yq --version` (should be v4+)
4. Test locally with the same data
5. Open an issue with debug logs

## License

Apache-2.0
