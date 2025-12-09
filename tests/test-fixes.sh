#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

# Test script to validate bug fixes in extract-metadata.sh
# This script tests the critical fixes without requiring a full GitHub Actions environment

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "Bug Fixes Validation Tests"
echo "============================================"
echo ""

# Track test results
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass() {
  echo "✅ PASS: $1"
  ((TESTS_PASSED++))
}

fail() {
  echo "❌ FAIL: $1"
  ((TESTS_FAILED++))
}

info() {
  echo "ℹ️  $1"
}

# Test 1: Verify no 'local' keyword outside functions
echo "Test 1: Checking for invalid 'local' usage outside functions"
echo "-----------------------------------------------------------"

# Use shellcheck to detect SC2168 (local outside function)
if command -v shellcheck &> /dev/null; then
  if shellcheck -S error "$ROOT_DIR/scripts/extract-metadata.sh" 2>&1 | grep -q "SC2168"; then
    fail "ShellCheck found 'local outside function' error (SC2168)"
  else
    pass "No 'local' keywords found outside function scope"
  fi
else
  info "ShellCheck not available, skipping this test"
fi
echo ""

# Test 2: Verify syntax is valid
echo "Test 2: Bash syntax validation"
echo "-----------------------------------------------------------"

if bash -n "$ROOT_DIR/scripts/extract-metadata.sh" 2>/dev/null; then
  pass "Bash syntax is valid"
else
  fail "Bash syntax errors detected"
fi
echo ""

# Test 3: Check for improved version tag regex
echo "Test 3: Semantic version tag regex improvement"
echo "-----------------------------------------------------------"

if grep -q 'v\[0-9\]+(\\\.\[0-9\]+){1,2}' "$ROOT_DIR/scripts/extract-metadata.sh"; then
  pass "Enhanced semantic version regex found"
else
  fail "Old version regex still in use"
fi
echo ""

# Test 4: Check for yq flavor detection
echo "Test 4: yq flavor detection"
echo "-----------------------------------------------------------"

if grep -q 'grep -q "mikefarah"' "$ROOT_DIR/scripts/extract-metadata.sh"; then
  pass "yq flavor detection implemented"
else
  fail "yq flavor detection not found"
fi
echo ""

# Test 5: Check for changed files array conversion
echo "Test 5: Changed files JSON array conversion"
echo "-----------------------------------------------------------"

if grep -q "jq -R -s 'split" "$ROOT_DIR/scripts/extract-metadata.sh" && \
   grep -q "CHANGED_FILES_ARRAY" "$ROOT_DIR/scripts/extract-metadata.sh"; then
  pass "Changed files array conversion implemented"
else
  fail "Changed files array conversion not found"
fi
echo ""

# Test 6: Check for multi-commit push detection
echo "Test 6: Multi-commit push detection (before/after SHA)"
echo "-----------------------------------------------------------"

# shellcheck disable=SC2016
if grep -q "\.before" "$ROOT_DIR/scripts/extract-metadata.sh" && \
   grep -q "\.after" "$ROOT_DIR/scripts/extract-metadata.sh" && \
   grep -q 'git diff --name-only "\$before_sha" "\$after_sha"' "$ROOT_DIR/scripts/extract-metadata.sh"; then
  pass "Multi-commit push detection implemented"
else
  fail "Multi-commit push detection not found"
fi
echo ""

# Test 7: Check for auto-detect default branch
echo "Test 7: Default branch auto-detection"
echo "-----------------------------------------------------------"

if grep -q "gh repo view.*defaultBranchRef" "$ROOT_DIR/scripts/extract-metadata.sh"; then
  pass "Default branch auto-detection implemented"
else
  fail "Default branch auto-detection not found"
fi
echo ""

# Test 8: Check for GitHub API pagination documentation
echo "Test 8: GitHub API pagination documentation"
echo "-----------------------------------------------------------"

if grep -qi "3000 files" "$ROOT_DIR/scripts/extract-metadata.sh"; then
  pass "GitHub API pagination limit documented"
else
  fail "GitHub API pagination documentation not found"
fi
echo ""

# Test 9: Validate newline preservation for changed files
echo "Test 9: Newline preservation for changed files"
echo "-----------------------------------------------------------"

# shellcheck disable=SC2016
if grep -q 'CHANGED_FILES="\$output"' "$ROOT_DIR/scripts/extract-metadata.sh"; then
  pass "Changed files preserve newline format"
else
  fail "Changed files may still convert to space-delimited"
fi
echo ""

# Test 10: ShellCheck validation for all critical errors (if available)
echo "Test 10: ShellCheck static analysis (optional)"
echo "-----------------------------------------------------------"

if command -v shellcheck &> /dev/null; then
  ERRORS=$(shellcheck -S error "$ROOT_DIR/scripts/extract-metadata.sh" 2>&1) || true
  if [ -z "$ERRORS" ]; then
    pass "ShellCheck found no critical errors"
  else
    fail "ShellCheck found critical errors"
    echo "$ERRORS" | head -20
  fi
else
  info "ShellCheck not available, skipping static analysis"
fi
echo ""

# Summary
echo "============================================"
echo "Test Summary"
echo "============================================"
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
  echo "✅ All tests passed!"
  exit 0
else
  echo "❌ Some tests failed. Please review the output above."
  exit 1
fi
