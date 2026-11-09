# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Tests for the dependency change guard in action.yaml.

The guard is the shell script of the 'Check dependency change inputs'
step. These tests run that script under bash with a controlled PATH
and read back what it writes to GITHUB_OUTPUT.
"""

import os
import shutil
import sys
from pathlib import Path
from subprocess import run
from typing import Any

import pytest
import yaml

ACTION = Path(__file__).resolve().parent.parent / "action.yaml"
STEP_NAME = "Check dependency change inputs"
BASH = shutil.which("bash")
GIT = shutil.which("git")

pytestmark = pytest.mark.skipif(
    BASH is None or GIT is None or os.name != "posix",
    reason="needs bash and git on a POSIX system",
)


def guard_step() -> dict[str, Any]:
    """Return the guard step from action.yaml."""
    action = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
    for step in action["runs"]["steps"]:
        if step.get("name") == STEP_NAME:
            return dict(step)
    raise AssertionError(f"No step named {STEP_NAME!r} in {ACTION}")


def executable(path: Path, body: str) -> Path:
    """Write an executable shell script at path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def run_guard(tmp_path: Path, path_entries: list[Path | str], interpreter: Path) -> dict[str, str]:
    """Run the guard with PATH set to path_entries and parse its outputs."""
    script = tmp_path / "guard.sh"
    step = guard_step()
    script.write_text(str(step["run"]), encoding="utf-8")
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    runner_temp = tmp_path / "runner_temp"
    runner_temp.mkdir(exist_ok=True)
    env = {
        "PATH": ":".join(str(entry) for entry in path_entries),
        "DEPENDENCY_CHANGE": "true",
        "SIDECAR": ".repository-metadata-dependency-change.json",
        "INTERPRETER": str(interpreter),
        "PYTHONEXECUTABLE": "",
        "__PYVENV_LAUNCHER__": "",
        "GIT_GUARD": str(step["env"]["GIT_GUARD"]),
        "GITHUB_OUTPUT": str(output),
        "GITHUB_WORKSPACE": str(workspace),
        "RUNNER_TEMP": str(runner_temp),
    }
    result = run(
        [str(BASH), "--noprofile", "--norc", "-eo", "pipefail", str(script)],
        cwd=workspace,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    outputs: dict[str, str] = {}
    for line in output.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        assert sep, f"Malformed GITHUB_OUTPUT line: {line!r}"
        assert key not in outputs, f"Duplicate output {key!r}"
        outputs[key] = value
    return outputs


@pytest.fixture
def trusted_dir(tmp_path: Path) -> Path:
    """A directory holding the trusted python3, outside the workspace."""
    directory = tmp_path / "python-bin"
    directory.mkdir()
    (directory / "python3").symlink_to(sys.executable)
    return directory


def test_trusted_lookups_run_detection(tmp_path: Path, trusted_dir: Path) -> None:
    """Control: a trusted python3 and a git outside the workspace pass."""
    git_dir = Path(str(GIT)).parent
    outputs = run_guard(tmp_path, [trusted_dir, git_dir], trusted_dir / "python3")
    assert outputs.get("run") == "true", outputs


def test_git_lookup_with_line_break_is_refused(tmp_path: Path, trusted_dir: Path) -> None:
    """A git candidate holding a line break is refused, not sanitised.

    Stripping the line break from 'workspace/b<LF>in/git' would check
    'workspace/bin/git', which links to a trusted git, while the
    detector would run the planted one.
    """
    workspace = tmp_path / "workspace"
    marker = tmp_path / "planted-git-ran"
    planted_dir = workspace / "b\nin"
    executable(planted_dir / "git", f"echo ran >> '{marker}'")
    decoy = workspace / "bin" / "git"
    decoy.parent.mkdir(parents=True)
    decoy.symlink_to(str(GIT))

    outputs = run_guard(tmp_path, [trusted_dir, planted_dir], trusted_dir / "python3")

    assert outputs.get("run") == "false", outputs
    reason = outputs.get("reason", "")
    assert reason.startswith("unresolved:"), reason
    assert "git candidate" in reason, reason
    assert "line break" in reason, reason
    assert "b\\nin/git" in reason, reason
    assert not marker.exists()


def test_python3_lookup_with_line_break_is_refused(tmp_path: Path, trusted_dir: Path) -> None:
    """A python3 lookup holding a line break is refused, not sanitised.

    Stripping the line break from 'python-<CR>bin/python3' would match
    the trusted interpreter's path.
    """
    planted_dir = tmp_path / "python-\rbin"
    executable(planted_dir / "python3", "exit 0")
    git_dir = Path(str(GIT)).parent

    outputs = run_guard(tmp_path, [planted_dir, trusted_dir, git_dir], trusted_dir / "python3")

    assert outputs.get("run") == "false", outputs
    reason = outputs.get("reason", "")
    assert reason.startswith("unresolved:"), reason
    assert "python3 lookup" in reason, reason
    assert "line break" in reason, reason


def assert_git_refused(outputs: dict[str, str], marker: Path, planted: Path | None = None) -> None:
    """Assert the guard refused a git candidate and never ran it."""
    assert outputs.get("run") == "false", outputs
    reason = outputs.get("reason", "")
    assert reason.startswith("unresolved: git candidate"), reason
    assert "inside the workspace or RUNNER_TEMP" in reason, reason
    if planted is not None:
        assert f"'{planted}'" in reason, reason
    assert not marker.exists()


@pytest.mark.parametrize("protected", ["workspace", "runner_temp"])
def test_git_inside_protected_directory_is_refused(
    tmp_path: Path, trusted_dir: Path, protected: str
) -> None:
    """A git inside the workspace or RUNNER_TEMP is refused."""
    marker = tmp_path / "planted-git-ran"
    planted_dir = tmp_path / protected / "bin"
    executable(planted_dir / "git", f"echo ran >> '{marker}'")

    outputs = run_guard(tmp_path, [trusted_dir, planted_dir], trusted_dir / "python3")

    assert_git_refused(outputs, marker)


def test_git_linked_into_workspace_is_refused(tmp_path: Path, trusted_dir: Path) -> None:
    """A link outside the workspace to a git inside it is refused."""
    marker = tmp_path / "planted-git-ran"
    planted = executable(tmp_path / "workspace" / "bin" / "git", f"echo ran >> '{marker}'")
    link_dir = tmp_path / "elsewhere"
    link_dir.mkdir()
    (link_dir / "git").symlink_to(planted)

    outputs = run_guard(tmp_path, [trusted_dir, link_dir], trusted_dir / "python3")

    assert_git_refused(outputs, marker)


def test_git_under_differently_cased_workspace_is_refused(
    tmp_path: Path, trusted_dir: Path
) -> None:
    """A git reached through another spelling of the workspace is refused.

    On a case-insensitive volume, such as macOS's default, the swapped
    case names the same directory, and a comparison of path text would
    pass it.
    """
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    alias = workspace.parent / workspace.name.swapcase()
    if not alias.exists() or not alias.samefile(workspace):
        pytest.skip("needs a case-insensitive filesystem")
    marker = tmp_path / "planted-git-ran"
    executable(workspace / "bin" / "git", f"echo ran >> '{marker}'")

    outputs = run_guard(tmp_path, [trusted_dir, alias / "bin"], trusted_dir / "python3")

    assert_git_refused(outputs, marker)


@pytest.mark.parametrize("first", ["broken", "working"])
def test_protected_git_behind_another_git_is_refused(
    tmp_path: Path, trusted_dir: Path, first: str
) -> None:
    """A workspace git later on PATH is refused, whatever comes first.

    Python's subprocess, which the detector uses, moves on to the next
    PATH entry when a git fails to start, such as one whose shebang
    names a missing interpreter, so checking the first git alone would
    let the planted one run.
    """
    marker = tmp_path / "planted-git-ran"
    first_dir = tmp_path / "elsewhere"
    first_dir.mkdir()
    if first == "broken":
        (first_dir / "git").write_text("#!/nonexistent/interpreter\n", encoding="utf-8")
        (first_dir / "git").chmod(0o755)
    else:
        (first_dir / "git").symlink_to(str(GIT))
    planted_dir = tmp_path / "workspace" / "bin"
    executable(planted_dir / "git", f"echo ran >> '{marker}'")
    path_entries: list[Path | str] = [trusted_dir, first_dir, planted_dir]

    outputs = run_guard(tmp_path, path_entries, trusted_dir / "python3")

    assert_git_refused(outputs, marker, planted_dir / "git")
    if first == "broken":
        # Control: subprocess does fall back to the planted git
        run(
            ["git", "status"],
            env={"PATH": ":".join(str(entry) for entry in path_entries)},
            check=True,
        )
        assert marker.exists()


@pytest.mark.parametrize("entry", ["", "."])
def test_relative_path_entry_is_refused(tmp_path: Path, trusted_dir: Path, entry: str) -> None:
    """A relative PATH entry is refused: it resolves in the detector's cwd."""
    marker = tmp_path / "planted-git-ran"
    executable(tmp_path / "workspace" / "git", f"echo ran >> '{marker}'")
    git_dir = Path(str(GIT)).parent

    outputs = run_guard(tmp_path, [trusted_dir, git_dir, entry], trusted_dir / "python3")

    assert outputs.get("run") == "false", outputs
    reason = outputs.get("reason", "")
    assert reason.startswith(f"unresolved: PATH entry '{entry}' is relative"), reason
    assert not marker.exists()


def test_protected_path_entry_without_git_passes(tmp_path: Path, trusted_dir: Path) -> None:
    """A RUNNER_TEMP entry holding no git, as setup-uv adds, is allowed."""
    tool_dir = tmp_path / "runner_temp" / "setup-uv-bin"
    executable(tool_dir / "uv", "exit 0")
    (tool_dir / "git").mkdir()
    git_dir = Path(str(GIT)).parent

    outputs = run_guard(tmp_path, [trusted_dir, tool_dir, git_dir], trusted_dir / "python3")

    assert outputs.get("run") == "true", outputs


def test_no_git_on_path_is_refused(tmp_path: Path, trusted_dir: Path) -> None:
    """With no executable git on PATH, detection is skipped."""
    outputs = run_guard(tmp_path, [trusted_dir], trusted_dir / "python3")

    assert outputs.get("run") == "false", outputs
    assert outputs.get("reason", "").startswith("unresolved: no executable git"), outputs
