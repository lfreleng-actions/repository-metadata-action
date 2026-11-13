# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""
Tests for the UV_NO_MODIFY_PATH refusal in action.yaml.

The refusal is the shell script of the 'Refuse an inherited
UV_NO_MODIFY_PATH' step, which must run before setup-uv. These tests
run that script under bash with a controlled environment.
"""

import os
import shlex
import shutil
from pathlib import Path
from subprocess import CompletedProcess, run
from typing import Any

import pytest
import yaml

ACTION = Path(__file__).resolve().parent.parent / "action.yaml"
STEP_NAME = "Refuse an inherited UV_NO_MODIFY_PATH"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(
    BASH is None or os.name != "posix",
    reason="needs bash on a POSIX system",
)


def steps() -> list[dict[str, Any]]:
    """Return the composite steps of action.yaml."""
    action = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
    return list(action["runs"]["steps"])


def step_index(name: str) -> int:
    """Return the position of the step with the given name."""
    for index, step in enumerate(steps()):
        if step.get("name") == name:
            return index
    raise AssertionError(f"No step named {name!r} in {ACTION}")


def shell_command(step: dict[str, Any], script: Path) -> list[str]:
    """Return the command a runner starts to run the step's script."""
    shell = str(step.get("shell", ""))
    if shell == "bash":
        shell = "bash --noprofile --norc -eo pipefail {0}"
    command = [arg.replace("{0}", str(script)) for arg in shlex.split(shell)]
    assert command and command[0] == "bash", f"Unexpected shell {shell!r}"
    command[0] = str(BASH)
    return command


def run_refusal(tmp_path: Path, extra: dict[str, str]) -> CompletedProcess[str]:
    """
    Run the refusal step with only PATH and extra inherited.

    The step's own shell and env apply, the env over the inherited one,
    as on a runner.
    """
    step = steps()[step_index(STEP_NAME)]
    script = tmp_path / "refuse.sh"
    script.write_text(str(step["run"]), encoding="utf-8")
    step_env = {key: str(value) for key, value in step.get("env", {}).items()}
    env = {"PATH": os.environ.get("PATH", ""), **extra, **step_env}
    return run(
        shell_command(step, script),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


@pytest.mark.xfail(strict=True, reason="refusal step not yet added")
def test_refusal_runs_before_setup_uv() -> None:
    """The refusal must come before setup-uv reads the variable."""
    assert step_index(STEP_NAME) < step_index("Install uv")


@pytest.mark.xfail(strict=True, reason="refusal step not yet added")
def test_unset_variable_passes(tmp_path: Path) -> None:
    """Control: without UV_NO_MODIFY_PATH the step succeeds."""
    result = run_refusal(tmp_path, {})
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.xfail(strict=True, reason="refusal step not yet added")
@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("UV_NO_MODIFY_PATH", "1"),
        ("UV_NO_MODIFY_PATH", ""),
        ("UV_NO_MODIFY_PATH", "false"),
        ("uv_no_modify_path", "1"),
    ],
)
def test_inherited_variable_is_refused(tmp_path: Path, name: str, value: str) -> None:
    """Any value, and any case of the name, stops the action."""
    result = run_refusal(tmp_path, {name: value})
    assert result.returncode == 1
    assert name in result.stdout


@pytest.mark.xfail(strict=True, reason="refusal step not yet added")
def test_inherited_bash_env_cannot_unset_variable(tmp_path: Path) -> None:
    """A caller's BASH_ENV must not unset the variable before the check."""
    startup = tmp_path / "startup.sh"
    startup.write_text("unset UV_NO_MODIFY_PATH\n", encoding="utf-8")
    result = run_refusal(tmp_path, {"UV_NO_MODIFY_PATH": "1", "BASH_ENV": str(startup)})
    assert result.returncode == 1
    assert "UV_NO_MODIFY_PATH" in result.stdout


@pytest.mark.xfail(strict=True, reason="function imports not yet disabled")
@pytest.mark.parametrize(
    ("function", "body"),
    [("compgen", "() { return 0; }"), ("read", "() { return 1; }")],
)
def test_inherited_function_cannot_hide_variable(tmp_path: Path, function: str, body: str) -> None:
    """A caller's exported function must not shadow a builtin the check uses."""
    result = run_refusal(tmp_path, {"UV_NO_MODIFY_PATH": "1", f"BASH_FUNC_{function}%%": body})
    assert result.returncode == 1
    assert "UV_NO_MODIFY_PATH" in result.stdout
