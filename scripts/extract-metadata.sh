#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

# GitHub Repository Metadata Extraction Script
# This script extracts comprehensive metadata about the GitHub repository

set -euo pipefail

# Configuration constants
# Depth for git fetch --deepen when shallow clone auto-fetch fails
# Default: 15 commits (configurable via git_fetch_depth input)
# This provides reasonable balance between fetch speed and finding
# the common ancestor for PRs (most PRs have fewer than 15 commits)
readonly GIT_DEEPEN_DEPTH="${GIT_FETCH_DEPTH:-15}"

# Initialize all variables with defaults
TAG_PUSH_EVENT="false"
IS_TAG_PUSH="false"
IS_BRANCH_PUSH="false"
IS_PULL_REQUEST="false"
IS_RELEASE="false"
IS_SCHEDULE="false"
IS_WORKFLOW_DISPATCH="false"
IS_FORK="false"
IS_DEFAULT_BRANCH="false"
IS_MAIN_BRANCH="false"
IS_PUBLIC="false"
IS_PRIVATE="false"
BRANCH_NAME=""
TAG_NAME=""
PR_NUMBER=""
PR_SOURCE_BRANCH=""
PR_TARGET_BRANCH=""
PR_COMMITS_COUNT=""
COMMIT_MESSAGE=""
COMMIT_AUTHOR=""
CHANGED_FILES=""
CHANGED_FILES_COUNT="0"

# Function to output debug information
debug_log() {
  if [ "${DEBUG_MODE}" = "true" ]; then
    echo "🔍 DEBUG: $*"
  fi
}

# Function to safely set output
set_output() {
  local name="$1"
  local value="$2"

  # Check if value contains newlines (multi-line)
  if [[ "$value" == *$'\n'* ]]; then
    # Use delimiter format for multi-line values
    local delimiter="EOF_${RANDOM}_${RANDOM}"
    {
      echo "${name}<<${delimiter}"
      echo "$value"
      echo "${delimiter}"
    } >> "$GITHUB_OUTPUT"
    debug_log "Set output: $name=<multiline>"
  else
    # Simple format for single-line values
    echo "${name}=${value}" >> "$GITHUB_OUTPUT"
    debug_log "Set output: $name=$value"
  fi
}

debug_log "Starting metadata extraction"

# Determine changed files detection method
if [ "${CHANGE_DETECTION}" = "git" ]; then
  echo "🔧 Input requested Git for changed files detection"
elif [ "${CHANGE_DETECTION}" = "github_api" ]; then
  echo "🔑 Input requested GitHub API for changed files detection"
elif [ -n "${GITHUB_TOKEN_INPUT}" ]; then
  echo "🔑 Using GitHub API for changed files detection"
else
  echo "🔧 Using Git for changed files detection"
fi

# ============================================================================
# REPOSITORY METADATA
# ============================================================================
echo '### 📦 Repository Data ###'
echo "Organization: $GITHUB_REPOSITORY_OWNER"
set_output "repository_owner" "${GITHUB_REPOSITORY_OWNER}"

REPOSITORY_NAME="${GITHUB_REPOSITORY#"$GITHUB_REPOSITORY_OWNER"/}"
echo "Repository: ${REPOSITORY_NAME}"
set_output "repository_name" "${REPOSITORY_NAME}"
set_output "repository_full_name" "${GITHUB_REPOSITORY}"

# Determine repository visibility
# Using github.event.repository.visibility context variable
REPO_VISIBILITY="${REPO_VISIBILITY:-}"
if [ "${REPO_VISIBILITY}" = "public" ]; then
  IS_PUBLIC="true"
  IS_PRIVATE="false"
elif [ "${REPO_VISIBILITY}" = "private" ]; then
  IS_PUBLIC="false"
  IS_PRIVATE="true"
elif [ "${REPO_VISIBILITY}" = "internal" ]; then
  IS_PUBLIC="false"
  IS_PRIVATE="true"
fi
set_output "is_public" "${IS_PUBLIC}"
set_output "is_private" "${IS_PRIVATE}"

# ============================================================================
# ACTOR METADATA
# ============================================================================
echo ""
echo '### 👤 Actor Data ###'
echo "Actor: ${GITHUB_ACTOR} [ID: ${GITHUB_ACTOR_ID}]"
set_output "actor" "${GITHUB_ACTOR}"
set_output "actor_id" "${GITHUB_ACTOR_ID}"

# ============================================================================
# COMMIT METADATA
# ============================================================================
echo ""
echo '### 📝 Commit Data ###'
COMMIT_SHA="${GITHUB_SHA}"
COMMIT_SHA_SHORT="${GITHUB_SHA:0:7}"
echo "Commit SHA: ${COMMIT_SHA}"
echo "Commit SHA (short): ${COMMIT_SHA_SHORT}"
set_output "commit_sha" "${COMMIT_SHA}"
set_output "commit_sha_short" "${COMMIT_SHA_SHORT}"

# Get commit message and author if we have git history
if [ -d ".git" ]; then
  COMMIT_MESSAGE=$(git log -1 --pretty=format:'%s' \
    2>/dev/null || echo "")
  COMMIT_AUTHOR=$(git log -1 --pretty=format:'%an' \
    2>/dev/null || echo "")
  if [ -n "${COMMIT_MESSAGE}" ]; then
    echo "Commit message: ${COMMIT_MESSAGE}"
  fi
  if [ -n "${COMMIT_AUTHOR}" ]; then
    echo "Commit author: ${COMMIT_AUTHOR}"
  fi
fi
set_output "commit_message" "${COMMIT_MESSAGE}"
set_output "commit_author" "${COMMIT_AUTHOR}"

# ============================================================================
# EVENT TYPE DETECTION
# ============================================================================
echo ""
echo '### 🎯 Event Type Detection ###'
EVENT_NAME="${GITHUB_EVENT_NAME}"
echo "Event name: ${EVENT_NAME}"
set_output "event_name" "${EVENT_NAME}"

case "${EVENT_NAME}" in
  pull_request|pull_request_target)
    IS_PULL_REQUEST="true"
    debug_log "Detected pull request event"
    ;;
  release|release_published|release_created)
    IS_RELEASE="true"
    debug_log "Detected release event"
    ;;
  schedule)
    IS_SCHEDULE="true"
    debug_log "Detected scheduled event"
    ;;
  workflow_dispatch)
    IS_WORKFLOW_DISPATCH="true"
    debug_log "Detected manual workflow dispatch"
    ;;
  push)
    debug_log "Detected push event"
    ;;
esac

set_output "is_pull_request" "${IS_PULL_REQUEST}"
set_output "is_release" "${IS_RELEASE}"
set_output "is_schedule" "${IS_SCHEDULE}"
set_output "is_workflow_dispatch" "${IS_WORKFLOW_DISPATCH}"

# ============================================================================
# GERRIT METADATA EXTRACTION
# ============================================================================
# Initialize Gerrit variables
GERRIT_SOURCE=""
GERRIT_BRANCH=""
GERRIT_CHANGE_ID=""
GERRIT_CHANGE_NUMBER=""
GERRIT_CHANGE_URL=""
GERRIT_EVENT_TYPE=""
GERRIT_PATCHSET_NUMBER=""
GERRIT_PATCHSET_REVISION=""
GERRIT_PROJECT=""
GERRIT_REFSPEC=""
GERRIT_COMMENT=""
GERRIT_JSON_INPUT=""
HAS_GERRIT_DATA="false"

# Process Gerrit data for workflow_dispatch events or check environment variables
if [ "${IS_WORKFLOW_DISPATCH}" = "true" ]; then
  echo ""
  echo '### 📋 Gerrit Metadata Detection ###'

  # Read the event payload (support override for tests)
  EVENT_PATH="${GITHUB_EVENT_PATH_OVERRIDE:-$GITHUB_EVENT_PATH}"
  if [ -f "$EVENT_PATH" ]; then
    EVENT_PAYLOAD=$(cat "$EVENT_PATH")

    # Check for gerrit_json input first (preferred method - consolidated JSON format)
    # Falls back to individual GERRIT_* inputs for backward compatibility #
    GERRIT_JSON_INPUT=$(echo "$EVENT_PAYLOAD" | jq -r '.inputs.gerrit_json // empty' 2>/dev/null || echo "")

    if [ -n "$GERRIT_JSON_INPUT" ] && [ "$GERRIT_JSON_INPUT" != "null" ]; then
      echo "🔍 Detected gerrit_json input"

      # Validate JSON
      if echo "$GERRIT_JSON_INPUT" | jq empty 2>/dev/null; then
        echo "✅ gerrit_json is valid JSON"
        GERRIT_SOURCE="Consolidated JSON variable"
        HAS_GERRIT_DATA="true"

        # Extract fields from JSON (using schema order)
        GERRIT_BRANCH=$(echo "$GERRIT_JSON_INPUT" | jq -r '.branch // empty')
        GERRIT_CHANGE_ID=$(echo "$GERRIT_JSON_INPUT" | jq -r '.change_id // empty')
        GERRIT_CHANGE_NUMBER=$(echo "$GERRIT_JSON_INPUT" | jq -r '.change_number // empty')
        GERRIT_CHANGE_URL=$(echo "$GERRIT_JSON_INPUT" | jq -r '.change_url // empty')
        GERRIT_EVENT_TYPE=$(echo "$GERRIT_JSON_INPUT" | jq -r '.event_type // empty')
        GERRIT_PATCHSET_NUMBER=$(echo "$GERRIT_JSON_INPUT" | jq -r '.patchset_number // empty')
        GERRIT_PATCHSET_REVISION=$(echo "$GERRIT_JSON_INPUT" | jq -r '.patchset_revision // empty')
        GERRIT_PROJECT=$(echo "$GERRIT_JSON_INPUT" | jq -r '.project // empty')
        GERRIT_REFSPEC=$(echo "$GERRIT_JSON_INPUT" | jq -r '.refspec // empty')
        GERRIT_COMMENT=$(echo "$GERRIT_JSON_INPUT" | jq -r '.comment // empty')

        echo "Extracted Gerrit data from JSON:"
        echo "  - branch: ${GERRIT_BRANCH}"
        echo "  - change_id: ${GERRIT_CHANGE_ID}"
        echo "  - change_number: ${GERRIT_CHANGE_NUMBER}"
        echo "  - project: ${GERRIT_PROJECT}"
      else
        echo "⚠️ WARNING: gerrit_json input contains invalid JSON"
        echo "Invalid JSON detected (content length: ${#GERRIT_JSON_INPUT} characters)"
        echo "Content has been redacted to prevent potential secret leakage"
        echo "Falling back to GERRIT_* inputs..."
        GERRIT_JSON_INPUT=""  # Clear invalid JSON
      fi
    fi

    # Fallback to GERRIT_* inputs if gerrit_json is not available or invalid
    if [ "$HAS_GERRIT_DATA" = "false" ]; then
      # Check if any GERRIT_* inputs exist
      GERRIT_INPUTS=$(echo "$EVENT_PAYLOAD" | jq -e '.inputs | keys[] | select(startswith("GERRIT_"))' 2>/dev/null | head -n1 || echo "")

      if [ -n "$GERRIT_INPUTS" ]; then
        echo "🔍 Detected GERRIT_* inputs"
        GERRIT_SOURCE="Workflow inputs/variables"
        HAS_GERRIT_DATA="true"

        # Extract all GERRIT_* inputs dynamically and map to schema fields
        GERRIT_BRANCH=$(echo "$EVENT_PAYLOAD" | jq -r '.inputs.GERRIT_BRANCH // empty')
        GERRIT_CHANGE_ID=$(echo "$EVENT_PAYLOAD" | jq -r '.inputs.GERRIT_CHANGE_ID // empty')
        GERRIT_CHANGE_NUMBER=$(echo "$EVENT_PAYLOAD" | jq -r '.inputs.GERRIT_CHANGE_NUMBER // empty')
        GERRIT_CHANGE_URL=$(echo "$EVENT_PAYLOAD" | jq -r '.inputs.GERRIT_CHANGE_URL // empty')
        GERRIT_EVENT_TYPE=$(echo "$EVENT_PAYLOAD" | jq -r '.inputs.GERRIT_EVENT_TYPE // empty')
        GERRIT_PATCHSET_NUMBER=$(echo "$EVENT_PAYLOAD" | jq -r '.inputs.GERRIT_PATCHSET_NUMBER // empty')
        GERRIT_PATCHSET_REVISION=$(echo "$EVENT_PAYLOAD" | jq -r '.inputs.GERRIT_PATCHSET_REVISION // empty')
        GERRIT_PROJECT=$(echo "$EVENT_PAYLOAD" | jq -r '.inputs.GERRIT_PROJECT // empty')
        GERRIT_REFSPEC=$(echo "$EVENT_PAYLOAD" | jq -r '.inputs.GERRIT_REFSPEC // empty')
        GERRIT_COMMENT=$(echo "$EVENT_PAYLOAD" | jq -r '.inputs.GERRIT_COMMENT // empty')

        echo "Extracted Gerrit data from workflow inputs:"
        echo "  - GERRIT_BRANCH: ${GERRIT_BRANCH}"
        echo "  - GERRIT_CHANGE_ID: ${GERRIT_CHANGE_ID}"
        echo "  - GERRIT_CHANGE_NUMBER: ${GERRIT_CHANGE_NUMBER}"
        echo "  - GERRIT_PROJECT: ${GERRIT_PROJECT}"
      else
        echo "ℹ️ No Gerrit inputs detected"
      fi
    fi
  else
    echo "⚠️ WARNING: Event payload file not found: ${EVENT_PATH}"
  fi
else
  # For non-workflow_dispatch events (like push), check for Gerrit environment variables
  # or extract from commit message
  debug_log "Checking for Gerrit environment variables"

  # Check if any GERRIT_* environment variables are set
  if [ -n "${GERRIT_BRANCH:-}" ] || [ -n "${GERRIT_CHANGE_ID:-}" ] || \
     [ -n "${GERRIT_CHANGE_NUMBER:-}" ] || [ -n "${GERRIT_PROJECT:-}" ]; then
    echo ""
    echo '### 📋 Gerrit Metadata Detection ###'
    echo "🔍 Detected GERRIT_* environment variables"
    GERRIT_SOURCE="Environment variables"
    HAS_GERRIT_DATA="true"

    echo "Extracted Gerrit data from environment:"
    echo "  - GERRIT_BRANCH: ${GERRIT_BRANCH}"
    echo "  - GERRIT_CHANGE_ID: ${GERRIT_CHANGE_ID}"
    echo "  - GERRIT_CHANGE_NUMBER: ${GERRIT_CHANGE_NUMBER}"
    echo "  - GERRIT_PROJECT: ${GERRIT_PROJECT}"
  else
    # Try to extract Change-Id from commit message
    debug_log "Checking commit message for Gerrit Change-Id"

    # Get the commit message
    COMMIT_MSG_FULL=$(git log -1 --format='%B' 2>/dev/null || echo "")

    # Extract Change-Id using sed (portable across BSD/macOS/Linux)
    EXTRACTED_CHANGE_ID=$(echo "$COMMIT_MSG_FULL" | sed -n 's/^Change-Id:[[:space:]]*\(I[0-9a-fA-F]\+\)$/\1/p' | head -n1)

    if [ -n "$EXTRACTED_CHANGE_ID" ]; then
      echo ""
      echo '### 📋 Gerrit Metadata Detection ###'
      echo "🔍 Detected Change-Id in commit message: ${EXTRACTED_CHANGE_ID}"
      GERRIT_SOURCE="Commit message trailer"
      HAS_GERRIT_DATA="true"

      GERRIT_CHANGE_ID="$EXTRACTED_CHANGE_ID"
      # For push events, use the branch name if available
      GERRIT_BRANCH="${BRANCH_NAME:-}"
      GERRIT_PROJECT=""
      GERRIT_CHANGE_NUMBER=""
      GERRIT_CHANGE_URL=""
      GERRIT_EVENT_TYPE="ref-updated"
      GERRIT_PATCHSET_NUMBER=""
      GERRIT_PATCHSET_REVISION="${COMMIT_SHA:-}"
      GERRIT_REFSPEC=""
      GERRIT_COMMENT=""

      echo "Extracted Gerrit data from commit:"
      echo "  - Change-Id: ${GERRIT_CHANGE_ID}"
      echo "  - Branch: ${GERRIT_BRANCH}"
      echo "  - Patchset revision: ${GERRIT_PATCHSET_REVISION}"
    else
      debug_log "No Gerrit Change-Id found in commit message"
    fi
  fi
fi

# Build and output gerrit_json
if [ "$HAS_GERRIT_DATA" = "true" ]; then
  # If we have valid JSON input, use it as-is
  if [ -n "$GERRIT_JSON_INPUT" ]; then
    # Use provided JSON; strip comment unless explicitly enabled
    if [ "${GERRIT_INCLUDE_COMMENT:-false}" = "true" ]; then
      GERRIT_JSON_OUTPUT="$GERRIT_JSON_INPUT"
    else
      GERRIT_JSON_OUTPUT="$(echo "$GERRIT_JSON_INPUT" | jq -c 'del(.comment)')"
    fi
    echo "✅ Using gerrit_json input as output"
  else
    # Build JSON from GERRIT_* variables
    GERRIT_JSON_OUTPUT=$(jq -n \
      --arg branch "$GERRIT_BRANCH" \
      --arg change_id "$GERRIT_CHANGE_ID" \
      --arg change_number "$GERRIT_CHANGE_NUMBER" \
      --arg change_url "$GERRIT_CHANGE_URL" \
      --arg event_type "$GERRIT_EVENT_TYPE" \
      --arg patchset_number "$GERRIT_PATCHSET_NUMBER" \
      --arg patchset_revision "$GERRIT_PATCHSET_REVISION" \
      --arg project "$GERRIT_PROJECT" \
      --arg refspec "$GERRIT_REFSPEC" \
      --arg comment "$GERRIT_COMMENT" \
      '{
        branch: $branch,
        change_id: $change_id,
        change_number: $change_number,
        change_url: $change_url,
        event_type: $event_type,
        patchset_number: $patchset_number,
        patchset_revision: $patchset_revision,
        project: $project,
        refspec: $refspec
      } + (if $comment != "" and env.GERRIT_INCLUDE_COMMENT == "true" then {comment: $comment} else {} end)')
    echo "✅ Built gerrit_json from GERRIT_* variables"
  fi

  # Set output
  set_output "gerrit_json" "${GERRIT_JSON_OUTPUT}"

  # Also store for use in metadata JSON/YAML (use parsed structure)
  GERRIT_ENV_JSON=$(echo "$GERRIT_JSON_OUTPUT" | jq -c .)
else
  # No Gerrit data
  set_output "gerrit_json" ""
  GERRIT_ENV_JSON=""
fi

# ============================================================================
# REF PARSING (Branch/Tag Detection)
# ============================================================================
echo ""
echo '### 🔀 Ref Data ###'

if [ -n "${GITHUB_REF:-}" ]; then
  echo "GitHub ref: ${GITHUB_REF}"
fi

if [ -n "${GITHUB_REF_TYPE:-}" ]; then
  echo "GitHub ref type: ${GITHUB_REF_TYPE}"

  if [ "${GITHUB_REF_TYPE}" = "tag" ]; then
    IS_TAG_PUSH="true"
    TAG_NAME="${GITHUB_REF_NAME:-}"
    echo "Tag name: ${TAG_NAME}"

    # Check if it's a version tag (starts with 'v' followed by numbers)
    if [[ "${TAG_NAME}" =~ ^v[0-9]+\.[0-9]+ ]]; then
      TAG_PUSH_EVENT="true"
      echo "Version tag: ${TAG_NAME}"
    fi
  elif [ "${GITHUB_REF_TYPE}" = "branch" ]; then
    IS_BRANCH_PUSH="true"
    BRANCH_NAME="${GITHUB_REF_NAME:-}"
    echo "Branch name: ${BRANCH_NAME}"

    # Check if this is main/master
    if [ "${BRANCH_NAME}" = "main" ] || \
       [ "${BRANCH_NAME}" = "master" ]; then
      IS_MAIN_BRANCH="true"
      echo "Main branch detected"
    fi
  fi
fi

set_output "is_tag_push" "${IS_TAG_PUSH}"
set_output "is_branch_push" "${IS_BRANCH_PUSH}"
set_output "tag_push_event" "${TAG_PUSH_EVENT}"
set_output "tag_name" "${TAG_NAME}"
set_output "branch_name" "${BRANCH_NAME}"
set_output "is_main_branch" "${IS_MAIN_BRANCH}"

# ============================================================================
# PULL REQUEST METADATA
# ============================================================================
if [ "${IS_PULL_REQUEST}" = "true" ]; then
  echo ""
  echo '### 🔄 Pull Request Data ###'

  # Extract PR number from GITHUB_REF (refs/pull/123/merge)
  if [[ "${GITHUB_REF:-}" =~ refs/pull/([0-9]+)/ ]]; then
    PR_NUMBER="${BASH_REMATCH[1]}"
    echo "PR number: ${PR_NUMBER}"

    # Get PR commits count if token is available
    if [ -n "${GITHUB_TOKEN_INPUT}" ]; then
      export GH_TOKEN="${GITHUB_TOKEN_INPUT}"
      PR_COMMITS_COUNT=$(gh pr view "${PR_NUMBER}" --json commits \
        --jq '.commits | length' 2>/dev/null || echo "")
      if [ -n "${PR_COMMITS_COUNT}" ]; then
        echo "PR commits count: ${PR_COMMITS_COUNT}"
      fi
    fi
  fi

  # Get source and target branches
  if [ -n "${GITHUB_HEAD_REF:-}" ]; then
    PR_SOURCE_BRANCH="${GITHUB_HEAD_REF}"
    echo "PR source branch: ${PR_SOURCE_BRANCH}"
  fi

  if [ -n "${GITHUB_BASE_REF:-}" ]; then
    PR_TARGET_BRANCH="${GITHUB_BASE_REF}"
    echo "PR target branch: ${PR_TARGET_BRANCH}"
  fi

  # Detect fork
  if [ "${PR_HEAD_REPO_FORK:-false}" = "true" ]; then
    IS_FORK="true"
    echo "PR is from a fork"
  fi

  set_output "pr_number" "${PR_NUMBER}"
  set_output "pr_source_branch" "${PR_SOURCE_BRANCH}"
  set_output "pr_target_branch" "${PR_TARGET_BRANCH}"
  set_output "is_fork" "${IS_FORK}"
  set_output "pr_commits_count" "${PR_COMMITS_COUNT}"
fi

# ============================================================================
# DEFAULT BRANCH DETECTION
# ============================================================================
# Check if current branch is the default branch
if [ -n "${BRANCH_NAME}" ]; then
  DEFAULT_BRANCH="${DEFAULT_BRANCH:-}"
  if [ "${BRANCH_NAME}" = "${DEFAULT_BRANCH}" ]; then
    IS_DEFAULT_BRANCH="true"
    echo "Running on default branch: ${DEFAULT_BRANCH}"
  fi
fi
set_output "is_default_branch" "${IS_DEFAULT_BRANCH}"

# ============================================================================
# CACHE KEY GENERATION
# ============================================================================
echo ""
echo '### 🔑 Cache Keys ###'

# Generate cache keys
CACHE_KEY="${GITHUB_REPOSITORY_OWNER}-${REPOSITORY_NAME}"
CACHE_KEY="${CACHE_KEY}-${GITHUB_REF_NAME:-main}-${COMMIT_SHA_SHORT}"
CACHE_RESTORE_KEY="${GITHUB_REPOSITORY_OWNER}-${REPOSITORY_NAME}"
CACHE_RESTORE_KEY="${CACHE_RESTORE_KEY}-${GITHUB_REF_NAME:-main}-"

echo "Cache key: ${CACHE_KEY}"
echo "Cache restore key: ${CACHE_RESTORE_KEY}"

set_output "cache_key" "${CACHE_KEY}"
set_output "cache_restore_key" "${CACHE_RESTORE_KEY}"

# ============================================================================
# CHANGED FILES DETECTION
# ============================================================================
echo ""
echo '### 📄 Changed Files ###'

# For pull requests, get changed files
if [ "${IS_PULL_REQUEST}" = "true" ] && [ -n "${PR_NUMBER}" ]; then
  debug_log "Attempting to fetch changed files for PR #${PR_NUMBER}"
  debug_log "GITHUB_TOKEN_INPUT length: ${#GITHUB_TOKEN_INPUT}"

  if [ -n "${GITHUB_TOKEN_INPUT}" ] && [ "${CHANGE_DETECTION}" != "git" ]; then
    # Token provided - use GitHub API via gh CLI
    if ! command -v gh &> /dev/null; then
      echo "❌ Error: GitHub token provided but 'gh' CLI is not available"
      exit 1
    fi

    # Export token for gh CLI to use
    export GH_TOKEN="${GITHUB_TOKEN_INPUT}"
    debug_log "Using gh CLI to fetch PR files"

    # Capture both stdout and stderr
    GH_OUTPUT=$(gh pr view "${PR_NUMBER}" --json files \
      --jq '.files[].path' 2>&1)
    GH_EXIT_CODE=$?

    if [ ${GH_EXIT_CODE} -ne 0 ]; then
      echo "⚠️ Warning: Failed to fetch PR files via GitHub API"
      echo "GitHub CLI output: ${GH_OUTPUT}"
      echo "Changed files will not be available"
      CHANGED_FILES=""
      CHANGED_FILES_COUNT="0"
    else
      CHANGED_FILES=$(echo "${GH_OUTPUT}" | tr '\n' ' ')
      CHANGED_FILES_COUNT=$(echo "${CHANGED_FILES}" | wc -w | tr -d ' ')
    fi

  elif [ -d ".git" ]; then
    # No token - fallback to git if available
    echo "⚠️ Warning: No GitHub token provided, using git fallback for changed files"
    debug_log "Using git to fetch changed files"

    # For PRs, GitHub Actions checks out a merge commit
    # Try multiple strategies to get the changed files
    GIT_OUTPUT=""

    # Check if this is a shallow clone
    IS_SHALLOW=$(git rev-parse --is-shallow-repository \
      2>/dev/null || echo "false")
    debug_log "Is shallow repository: ${IS_SHALLOW}"

    # If shallow and we have GITHUB_BASE_REF, try to fetch enough
    # depth
    if [ "${IS_SHALLOW}" = "true" ] && \
      [ -n "${GITHUB_BASE_REF:-}" ]; then
      echo "Detected shallow clone, fetching base branch for diff..."
      debug_log "Fetching origin/${GITHUB_BASE_REF}"

      # Fetch the base branch with depth=1 (minimal fetch)
      if git fetch --depth=1 origin \
        "${GITHUB_BASE_REF}:refs/remotes/origin/${GITHUB_BASE_REF}" \
        2>/dev/null; then
        debug_log "Successfully fetched base branch"
      else
        debug_log "Failed to fetch base branch, trying deepen"
        # Try deepening the current history to find common ancestor
        # This fetches additional commits to help git diff find the merge base
        git fetch --deepen="${GIT_DEEPEN_DEPTH}" 2>/dev/null || true
      fi
    fi

    # Strategy 1: Use GITHUB_BASE_REF if available (PR base branch)
    if [ -n "${GITHUB_BASE_REF:-}" ]; then
      debug_log "Git diff with GITHUB_BASE_REF: ${GITHUB_BASE_REF}"
      if GIT_OUTPUT=$(git diff --name-only \
        "origin/${GITHUB_BASE_REF}...HEAD" 2>/dev/null); then
        debug_log "Successfully got files using GITHUB_BASE_REF"
      fi
    fi

    # Strategy 2: Try HEAD^1 (first parent of merge commit)
    if [ -z "${GIT_OUTPUT}" ]; then
      debug_log "Git diff with HEAD^1"
      if GIT_OUTPUT=$(git diff --name-only HEAD^1 2>/dev/null); then
        debug_log "Successfully got files using HEAD^1"
      fi
    fi

    # Strategy 3: For merge commits, use git show with merge diff
    if [ -z "${GIT_OUTPUT}" ]; then
      debug_log "Trying git show for merge commit"
      if GIT_OUTPUT=$(git show --pretty="" --name-only HEAD \
        2>/dev/null); then
        debug_log "Successfully got files using git show"
      fi
    fi

    # Strategy 4: Get all files in the last commit using diff-tree
    if [ -z "${GIT_OUTPUT}" ]; then
      debug_log "Git diff-tree"
      if GIT_OUTPUT=$(git diff-tree --no-commit-id --name-only -r \
        HEAD 2>/dev/null); then
        debug_log "Successfully got files using diff-tree"
      fi
    fi

    # If all strategies failed, warn but continue
    if [ -z "${GIT_OUTPUT}" ]; then
      echo "⚠️ Warning: Unable to detect changed files using git"
      echo "Tried: origin/${GITHUB_BASE_REF:-${PR_TARGET_BRANCH}}, HEAD^1, git show, and diff-tree"
      echo "Consider using fetch-depth: 0 or providing github_token"
      echo "Changed files will not be available"
      CHANGED_FILES=""
      CHANGED_FILES_COUNT="0"
    else
      CHANGED_FILES=$(echo "${GIT_OUTPUT}" | tr '\n' ' ')
      CHANGED_FILES_COUNT=$(echo "${CHANGED_FILES}" | wc -w | tr -d ' ')
    fi
  else
    echo "⚠️ Warning: Cannot detect changed files - no GitHub token and no git repository"
    debug_log "No method available to fetch changed files"
  fi
elif [ "${IS_BRANCH_PUSH}" = "true" ] && [ -d ".git" ]; then
  # For push events, get files changed in the last commit
  debug_log "Attempting to fetch changed files for push event"

  if ! GIT_OUTPUT=$(git diff-tree --no-commit-id --name-only -r \
    HEAD 2>&1); then
    echo "⚠️ Warning: git diff-tree failed to fetch changed files"
    echo "Git output: ${GIT_OUTPUT}"
    echo "Changed files will not be available"
    CHANGED_FILES=""
    CHANGED_FILES_COUNT="0"
  else
    CHANGED_FILES=$(echo "${GIT_OUTPUT}" | tr '\n' ' ')
    CHANGED_FILES_COUNT=$(echo "${CHANGED_FILES}" | wc -w | tr -d ' ')
  fi
fi

if [ -n "${CHANGED_FILES}" ]; then
  echo "Changed files count: ${CHANGED_FILES_COUNT}"
  if [ "${DEBUG_MODE}" = "true" ]; then
    echo "Changed files: ${CHANGED_FILES}"
  fi
else
  debug_log "No changed files detected"
  echo "Changed files count: 0"
fi

set_output "changed_files" "${CHANGED_FILES}"
set_output "changed_files_count" "${CHANGED_FILES_COUNT}"

# ============================================================================
# JSON OUTPUT
# ============================================================================
echo ""
echo '### 📋 JSON Metadata ###'

# Build JSON output with all metadata
# Using jq for safe JSON construction to handle special characters
# -c flag produces compact output (single line)
# Build base JSON first
BASE_JSON=$(jq -nc \
  --arg repo_owner "${GITHUB_REPOSITORY_OWNER}" \
  --arg repo_name "${REPOSITORY_NAME}" \
  --arg repo_full "${GITHUB_REPOSITORY}" \
  --argjson is_public "${IS_PUBLIC}" \
  --argjson is_private "${IS_PRIVATE}" \
  --arg event_name "${EVENT_NAME}" \
  --argjson is_tag_push "${IS_TAG_PUSH}" \
  --argjson is_branch_push "${IS_BRANCH_PUSH}" \
  --argjson is_pull_request "${IS_PULL_REQUEST}" \
  --argjson is_release "${IS_RELEASE}" \
  --argjson is_schedule "${IS_SCHEDULE}" \
  --argjson is_workflow_dispatch "${IS_WORKFLOW_DISPATCH}" \
  --argjson tag_push_event "${TAG_PUSH_EVENT}" \
  --arg branch_name "${BRANCH_NAME}" \
  --arg tag_name "${TAG_NAME}" \
  --argjson is_default_branch "${IS_DEFAULT_BRANCH}" \
  --argjson is_main_branch "${IS_MAIN_BRANCH}" \
  --arg commit_sha "${COMMIT_SHA}" \
  --arg commit_sha_short "${COMMIT_SHA_SHORT}" \
  --arg commit_message "${COMMIT_MESSAGE}" \
  --arg commit_author "${COMMIT_AUTHOR}" \
  --arg pr_number "${PR_NUMBER}" \
  --arg pr_source_branch "${PR_SOURCE_BRANCH}" \
  --arg pr_target_branch "${PR_TARGET_BRANCH}" \
  --argjson is_fork "${IS_FORK}" \
  --arg actor_name "${GITHUB_ACTOR}" \
  --arg actor_id "${GITHUB_ACTOR_ID}" \
  --arg cache_key "${CACHE_KEY}" \
  --arg cache_restore_key "${CACHE_RESTORE_KEY}" \
  --argjson changed_files_count "${CHANGED_FILES_COUNT}" \
  --arg changed_files "${CHANGED_FILES}" \
  '{
    "repository": {
      "owner": $repo_owner,
      "name": $repo_name,
      "full_name": $repo_full,
      "is_public": $is_public,
      "is_private": $is_private
    },
    "event": {
      "name": $event_name,
      "is_tag_push": $is_tag_push,
      "is_branch_push": $is_branch_push,
      "is_pull_request": $is_pull_request,
      "is_release": $is_release,
      "is_schedule": $is_schedule,
      "is_workflow_dispatch": $is_workflow_dispatch,
      "tag_push_event": $tag_push_event
    },
    "ref": {
      "branch_name": $branch_name,
      "tag_name": $tag_name,
      "is_default_branch": $is_default_branch,
      "is_main_branch": $is_main_branch
    },
    "commit": {
      "sha": $commit_sha,
      "sha_short": $commit_sha_short,
      "message": $commit_message,
      "author": $commit_author
    },
    "pull_request": {
      "number": (
        if $pr_number == "" then null
        else $pr_number | tonumber
        end
      ),
      "source_branch": $pr_source_branch,
      "target_branch": $pr_target_branch,
      "is_fork": $is_fork
    },
    "actor": {
      "name": $actor_name,
      "id": (
        if $actor_id == "" then null
        else $actor_id | tonumber
        end
      )
    },
    "cache": {
      "key": $cache_key,
      "restore_key": $cache_restore_key
    },
    "changed_files": {
      "count": $changed_files_count,
      "files": $changed_files
    }
  }')

# Add gerrit_environment if available
if [ "$HAS_GERRIT_DATA" = "true" ] && [ -n "$GERRIT_ENV_JSON" ]; then
  METADATA_JSON=$(echo "$BASE_JSON" | jq \
    --argjson gerrit_env "$GERRIT_ENV_JSON" \
    '. + {gerrit_environment: $gerrit_env}')
else
  METADATA_JSON="$BASE_JSON"
fi

if [ "${DEBUG_MODE}" = "true" ]; then
  echo "Metadata JSON:"
  echo "${METADATA_JSON}" | jq .
fi

set_output "metadata_json" "${METADATA_JSON}"

# ============================================================================
# YAML OUTPUT
# ============================================================================
echo ""
echo '### 📋 YAML Metadata ###'

# Convert JSON to YAML using yq
# yq is pre-installed on GitHub-hosted runners
METADATA_YAML=$(echo "${METADATA_JSON}" | yq -P .)

if [ "${DEBUG_MODE}" = "true" ]; then
  echo "Metadata YAML:"
  echo "${METADATA_YAML}"
fi

set_output "metadata_yaml" "${METADATA_YAML}"

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo '### ✅ Summary ###'
echo "Repository: ${GITHUB_REPOSITORY}"
echo "Event: ${EVENT_NAME}"
if [ "${IS_TAG_PUSH}" = "true" ]; then
  echo "Tag: ${TAG_NAME}"
else
  echo "Branch: ${BRANCH_NAME}"
fi
echo "Commit: ${COMMIT_SHA_SHORT}"
echo "Actor: ${GITHUB_ACTOR}"

debug_log "Metadata extraction complete"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
# Function to sanitize values for safe inclusion in markdown tables
sanitize_table_value() {
  echo "$1" | tr -d '\r' | tr '\n' ' ' | sed "s/\`/\\\`/g; s/|/\\|/g"
}

# ============================================================================
# GITHUB STEP SUMMARY (Optional)
# ============================================================================
if [ "${GENERATE_SUMMARY}" = "true" ]; then
  echo ""
  echo "Generating GitHub Step Summary..."

  {
    echo '## Repository Metadata'
    echo ''

    echo '### 📦 Repository Outputs'
    echo "✅ repository_owner: ${GITHUB_REPOSITORY_OWNER}"
    echo "✅ repository_name: ${REPOSITORY_NAME}"
    echo "✅ repository_full_name: ${GITHUB_REPOSITORY}"
    echo "✅ is_public: ${IS_PUBLIC}"
    echo "✅ is_private: ${IS_PRIVATE}"
    echo ''

    echo '### 🎯 Event Type Outputs'
    echo "✅ event_name: ${EVENT_NAME}"
    echo "✅ tag_push_event: ${TAG_PUSH_EVENT}"
    echo "✅ is_tag_push: ${IS_TAG_PUSH}"
    echo "✅ is_branch_push: ${IS_BRANCH_PUSH}"
    echo "✅ is_pull_request: ${IS_PULL_REQUEST}"
    echo "✅ is_release: ${IS_RELEASE}"
    echo "✅ is_schedule: ${IS_SCHEDULE}"
    echo "✅ is_workflow_dispatch: ${IS_WORKFLOW_DISPATCH}"
    echo ''

    echo '### 🔀 Branch/Tag Outputs'
    echo "✅ branch_name: ${BRANCH_NAME}"
    echo "✅ tag_name: ${TAG_NAME}"
    echo "✅ is_default_branch: ${IS_DEFAULT_BRANCH}"
    echo "✅ is_main_branch: ${IS_MAIN_BRANCH}"
    echo ''

    echo '### 📝 Commit Outputs'
    echo "✅ commit_sha: ${COMMIT_SHA}"
    echo "✅ commit_sha_short: ${COMMIT_SHA_SHORT}"
    echo "✅ commit_message: ${COMMIT_MESSAGE}"
    echo "✅ commit_author: ${COMMIT_AUTHOR}"
    echo ''

    echo '### 🔄 Pull Request Outputs'
    echo "✅ pr_number: ${PR_NUMBER}"
    echo "✅ pr_source_branch: ${PR_SOURCE_BRANCH}"
    echo "✅ pr_target_branch: ${PR_TARGET_BRANCH}"
    echo "✅ is_fork: ${IS_FORK}"
    echo "✅ pr_commits_count: ${PR_COMMITS_COUNT}"
    echo ''

    echo '### 👤 Actor Outputs'
    echo "✅ actor: ${GITHUB_ACTOR}"
    echo "✅ actor_id: ${GITHUB_ACTOR_ID}"
    echo ''

    echo '### 🔑 Cache Outputs'
    echo "✅ cache_key: ${CACHE_KEY}"
    echo "✅ cache_restore_key: ${CACHE_RESTORE_KEY}"
    echo ''

    echo '### 📄 Changed Files Outputs'
    echo "✅ changed_files: ${CHANGED_FILES}"
    echo "✅ changed_files_count: ${CHANGED_FILES_COUNT}"
    echo ''
  } >> "$GITHUB_STEP_SUMMARY"
fi

# ============================================================================
# GERRIT STEP SUMMARY (Optional)
# ============================================================================
if [ "${GERRIT_SUMMARY}" = "true" ] && [ "$HAS_GERRIT_DATA" = "true" ]; then
  echo ""
  echo "Generating Gerrit Parameters Summary..."

  {
    echo '### 📋 Gerrit Parameters'
    echo ''
    echo "**Source:** $(sanitize_table_value "${GERRIT_SOURCE}")"
    echo ''
    echo '| Gerrit Change Property | Value |'
    echo '|------------------------|-------|'
    echo "| branch | \`$(sanitize_table_value "${GERRIT_BRANCH}")\` |"
    echo "| change_id | \`$(sanitize_table_value "${GERRIT_CHANGE_ID}")\` |"
    echo "| change_number | \`$(sanitize_table_value "${GERRIT_CHANGE_NUMBER}")\` |"
    echo "| change_url | \`$(sanitize_table_value "${GERRIT_CHANGE_URL}")\` |"
    echo "| event_type | \`$(sanitize_table_value "${GERRIT_EVENT_TYPE}")\` |"
    echo "| patchset_number | \`$(sanitize_table_value "${GERRIT_PATCHSET_NUMBER}")\` |"
    echo "| patchset_revision | \`$(sanitize_table_value "${GERRIT_PATCHSET_REVISION}")\` |"
    echo "| project | \`$(sanitize_table_value "${GERRIT_PROJECT}")\` |"
    echo "| refspec | \`$(sanitize_table_value "${GERRIT_REFSPEC}")\` |"
    # Conditionally include a truncated, escaped comment only when explicitly enabled
    if [ "${GERRIT_INCLUDE_COMMENT:-false}" = "true" ]; then
      TRUNCATED_COMMENT="$(printf "%s" "${GERRIT_COMMENT}" | cut -c 1-200)"
      echo "| comment | \`$(sanitize_table_value "${TRUNCATED_COMMENT}")\` |"
    fi
    echo ''
  } >> "$GITHUB_STEP_SUMMARY"
fi

# ============================================================================
# UPLOAD ARTIFACT (Optional)
# ============================================================================
if [ "${ARTIFACT_UPLOAD}" = "true" ]; then
  echo ""
  echo "Uploading metadata as artifact..."

  # Parse artifact formats (default: json,yaml)
  ARTIFACT_FORMATS="${ARTIFACT_FORMATS:-json,yaml}"
  debug_log "Artifact formats: ${ARTIFACT_FORMATS}"

  # Generate unique suffix to avoid conflicts when action is called multiple times
  # 4 alphanumeric characters (64 bytes ensures reliable filtering to 4 chars)
  ARTIFACT_SUFFIX=$(head -c 64 /dev/urandom | tr -dc 'a-z0-9' | head -c 4)
  set_output "artifact_suffix" "${ARTIFACT_SUFFIX}"

  # Create artifact directory
  ARTIFACT_DIR="${RUNNER_TEMP}/repository-metadata-${ARTIFACT_SUFFIX}"
  mkdir -p "${ARTIFACT_DIR}"

  # Write JSON files if requested
  if [[ "${ARTIFACT_FORMATS}" == *"json"* ]]; then
    # Write compact JSON
    echo "${METADATA_JSON}" > "${ARTIFACT_DIR}/metadata.json"

    # Pretty-print for human readability
    echo "${METADATA_JSON}" | \
      jq . > "${ARTIFACT_DIR}/metadata-pretty.json"
  fi

  # Write YAML file if requested
  if [[ "${ARTIFACT_FORMATS}" == *"yaml"* ]]; then
    echo "${METADATA_YAML}" > "${ARTIFACT_DIR}/metadata.yaml"
  fi

  echo "Metadata saved to ${ARTIFACT_DIR}"
  debug_log "Artifact files created: $(ls "${ARTIFACT_DIR}")"

  # Set output for artifact path
  echo "artifact_path=${ARTIFACT_DIR}" >> "$GITHUB_OUTPUT"
fi
