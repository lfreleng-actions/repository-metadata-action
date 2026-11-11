# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Tests that the metadata step runs only the git the action approved.

The 'Extract Repository Metadata' step drops the caller's GIT_*
variables and pins GitPython to the approved git; src.main runs that
git, or none at all. These tests run the step's script with a stand-in
interpreter, and run src.main in a child process so that its imports
start from an empty sys.modules.
"""

import json
import os
import shutil
import sys
from pathlib import Path
from subprocess import run
from typing import Any

import pytest
import yaml

import src.config
from src.config import Config

ROOT = Path(__file__).resolve().parent.parent
ACTION = ROOT / "action.yaml"
STEP_NAME = "Extract Repository Metadata"
BASH = shutil.which("bash")
GIT = shutil.which("git")

pytestmark = pytest.mark.skipif(
    BASH is None or GIT is None or os.name != "posix",
    reason="needs bash and git on a POSIX system",
)

# Runs main() as the action does and reports whether GitPython loaded
DRIVER = """
import sys
from src.main import main
code = main()
print("GIT_IMPORTED=" + str("git" in sys.modules))
sys.exit(code)
"""


def metadata_step() -> dict[str, Any]:
    """Return the metadata step from action.yaml."""
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


def recording_git(path: Path, marker: Path) -> Path:
    """Write a git that appends the name it ran as, then runs git."""
    return executable(path, f"echo \"$0\" >> '{marker}'\nexec '{GIT}' \"$@\"")


def run_metadata_step(tmp_path: Path, step_env: dict[str, str]) -> dict[str, str]:
    """Run the step's script under a hostile caller environment.

    The stand-in interpreter records the environment src.main would
    see. Returns that environment.
    """
    script = tmp_path / "metadata.sh"
    script.write_text(str(metadata_step()["run"]), encoding="utf-8")
    dump = tmp_path / "environment.json"
    interpreter = executable(
        tmp_path / "interpreter",
        f"exec '{sys.executable}' -c "
        "'import json, os, sys; json.dump(dict(os.environ), open(sys.argv[1], \"w\"))' "
        f"'{dump}'",
    )
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        # Caller settings that redirect git, or GitPython's choice of it
        "GIT_DIR": str(tmp_path / "hostile.git"),
        "GIT_EXEC_PATH": str(tmp_path / "hostile-exec"),
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": "/bin/false",
        "GIT_PYTHON_GIT_EXECUTABLE": str(tmp_path / "caller-git"),
        "GIT_PYTHON_REFRESH": "quiet",
        "GIT_FETCH_DEPTH": "999",
        "PYTHONPATH": str(tmp_path),
        "GITHUB_TOKEN_INPUT": "token-value",
        "GITHUB_WORKSPACE": str(tmp_path),
        "INTERPRETER": str(interpreter),
        "FETCH_DEPTH_INPUT": "25",
        **step_env,
    }
    result = run(
        [str(BASH), "--noprofile", "--norc", "-eo", "pipefail", str(script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    environment: dict[str, str] = json.loads(dump.read_text(encoding="utf-8"))
    return environment


def test_metadata_step_pins_the_trusted_git(tmp_path: Path) -> None:
    """Only the action's own GIT_* settings reach src.main."""
    env = run_metadata_step(tmp_path, {"TRUSTED_GIT": str(GIT), "TRUSTED_GIT_PROBLEM": ""})

    git_vars = {name for name in env if name.startswith("GIT_")}
    assert git_vars == {"GIT_PYTHON_GIT_EXECUTABLE", "GIT_PYTHON_REFRESH", "GIT_FETCH_DEPTH"}
    assert env["GIT_PYTHON_GIT_EXECUTABLE"] == str(GIT)
    assert env["GIT_PYTHON_REFRESH"] == "error"
    assert env["GIT_FETCH_DEPTH"] == "25"
    assert not env.get("TRUSTED_GIT_PROBLEM")
    # GITHUB_* is not GIT_*, and PYTHON* still goes
    assert env["GITHUB_TOKEN_INPUT"] == "token-value"
    assert "PYTHONPATH" not in env


@pytest.mark.parametrize("problem", ["no executable git on PATH", ""])
def test_metadata_step_without_trusted_git(tmp_path: Path, problem: str) -> None:
    """Without an approved git, src.main gets a reason and no git."""
    env = run_metadata_step(tmp_path, {"TRUSTED_GIT": "", "TRUSTED_GIT_PROBLEM": problem})

    assert "GIT_PYTHON_GIT_EXECUTABLE" not in env
    assert "GIT_DIR" not in env
    assert env["GIT_PYTHON_REFRESH"] == "error"
    assert env["TRUSTED_GIT_PROBLEM"]
    if problem:
        assert env["TRUSTED_GIT_PROBLEM"] == problem


def test_git_fetch_depth_reaches_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The git_fetch_depth input survives the GIT_* filter into Config."""
    env = run_metadata_step(tmp_path, {"TRUSTED_GIT": str(GIT), "TRUSTED_GIT_PROBLEM": ""})
    monkeypatch.setenv("GIT_FETCH_DEPTH", env["GIT_FETCH_DEPTH"])
    for name, value in {
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_SHA": "a" * 40,
        "GITHUB_REPOSITORY_OWNER": "owner",
        "GITHUB_ACTOR": "testuser",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_OUTPUT": str(tmp_path / "output.txt"),
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(src.config, "_config_instance", None)

    assert Config().GIT_FETCH_DEPTH == 25


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A checkout with two commits, made with the real git."""
    path = tmp_path / "workspace"
    path.mkdir()
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test Author",
        "GIT_AUTHOR_EMAIL": "author@example.invalid",
        "GIT_COMMITTER_NAME": "Test Author",
        "GIT_COMMITTER_EMAIL": "author@example.invalid",
    }

    def git(*args: str) -> None:
        run([str(GIT), *args], cwd=path, env=env, check=True, capture_output=True)

    git("init", "-q")
    (path / "first.txt").write_text("one\n", encoding="utf-8")
    git("add", "first.txt")
    git("commit", "-q", "-m", "First commit")
    (path / "second.txt").write_text("two\n", encoding="utf-8")
    git("add", "second.txt")
    git("commit", "-q", "-m", "Add the second file")
    return path


def run_main(tmp_path: Path, workspace: Path, extra: dict[str, str]) -> tuple[Any, dict[str, str]]:
    """Run src.main in a child process with a planted git first on PATH.

    Returns the finished process and the outputs it wrote.
    """
    planted = recording_git(tmp_path / "planted" / "git", tmp_path / "planted-git-ran")
    head = run(
        [str(GIT), "rev-parse", "HEAD"], cwd=workspace, capture_output=True, text=True, check=True
    ).stdout.strip()
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    env = {
        "PATH": f"{planted.parent}:{os.environ.get('PATH', '/usr/bin:/bin')}",
        "HOME": str(tmp_path),
        "GITHUB_REPOSITORY": "owner/repo",
        "GITHUB_SHA": head,
        "GITHUB_REPOSITORY_OWNER": "owner",
        "GITHUB_ACTOR": "testuser",
        "GITHUB_EVENT_NAME": "push",
        "GITHUB_OUTPUT": str(output),
        "GITHUB_WORKSPACE": str(workspace),
        "ARTIFACT_UPLOAD": "false",
        "GERRIT_SUMMARY": "false",
        **extra,
    }
    result = run(
        [sys.executable, "-c", DRIVER],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    outputs: dict[str, str] = {}
    lines = iter(output.read_text(encoding="utf-8").splitlines())
    for line in lines:
        name, sep, value = line.partition("=")
        if sep and "<<" not in name:
            outputs[name] = value
            continue
        name, _, delimiter = line.partition("<<")
        body: list[str] = []
        for part in lines:
            if part == delimiter:
                break
            body.append(part)
        outputs[name] = "\n".join(body)
    return result, outputs


def warnings_of(stdout: str) -> list[str]:
    """Return the workflow warning commands in stdout."""
    return [line for line in stdout.splitlines() if line.startswith("::warning::")]


def assert_ran_without_git(tmp_path: Path, result: Any, outputs: dict[str, str]) -> None:
    """Assert main warned once, ran no git, and still wrote outputs."""
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "planted-git-ran").exists()
    warnings = warnings_of(result.stdout)
    assert len(warnings) == 1, result.stdout
    assert "git" in warnings[0]
    assert json.loads(outputs["metadata_json"])["repository"]
    assert outputs["commit_message"] == ""
    assert outputs["changed_files_last_commit"] == ""


def test_main_without_trusted_git_runs_no_git(tmp_path: Path, workspace: Path) -> None:
    """With no approved git, src.main never loads GitPython."""
    result, outputs = run_main(
        tmp_path, workspace, {"TRUSTED_GIT_PROBLEM": "no executable git on PATH"}
    )

    assert_ran_without_git(tmp_path, result, outputs)
    assert "GIT_IMPORTED=False" in result.stdout
    assert "no executable git on PATH" in warnings_of(result.stdout)[0]


def test_main_when_trusted_git_cannot_start(tmp_path: Path, workspace: Path) -> None:
    """An approved git that cannot start leaves git out; no fallback runs."""
    broken = tmp_path / "broken" / "git"
    broken.parent.mkdir()
    broken.write_text("#!/nonexistent/interpreter\n", encoding="utf-8")
    broken.chmod(0o755)

    result, outputs = run_main(
        tmp_path,
        workspace,
        {"GIT_PYTHON_GIT_EXECUTABLE": str(broken), "GIT_PYTHON_REFRESH": "error"},
    )

    assert_ran_without_git(tmp_path, result, outputs)


def test_main_runs_the_approved_git(tmp_path: Path, workspace: Path) -> None:
    """GitPython runs the approved git by its resolved path, never PATH's."""
    marker = tmp_path / "trusted-git-ran"
    wrapper = recording_git(tmp_path / "impl" / "git-wrapper", marker)
    link = tmp_path / "first" / "git"
    link.parent.mkdir()
    link.symlink_to(wrapper)

    result, outputs = run_main(
        tmp_path,
        workspace,
        {"GIT_PYTHON_GIT_EXECUTABLE": str(link), "GIT_PYTHON_REFRESH": "error"},
    )

    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "planted-git-ran").exists()
    assert warnings_of(result.stdout) == []
    names = set(marker.read_text(encoding="utf-8").splitlines())
    assert names == {os.path.realpath(wrapper)}
    assert outputs["commit_message"] == "Add the second file"
    assert outputs["changed_files_last_commit"] == "second.txt"
