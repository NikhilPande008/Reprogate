from types import SimpleNamespace
from pathlib import Path

import pytest

from triage.sandbox.container import CodexAgentUnavailable, CodexSandboxUnavailable, ContainerRole, DockerSandboxContainer


class FakeContainer:
    id = "container-1"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.commands = []

    def exec_run(self, command, demux=False):
        self.commands.append(command)
        return next(self.responses)


def _result(exit_code: int, output: str):
    return SimpleNamespace(exit_code=exit_code, output=output.encode())


def test_codex_uses_workspace_write_when_bwrap_is_available() -> None:
    container = FakeContainer([_result(0, "changed tests/test_target.py")])
    sandbox = DockerSandboxContainer(container, 60)

    execution = sandbox.run_codex("make a focused test", 30)

    assert execution.fallback is None
    assert "--sandbox workspace-write" in container.commands[0][-1]
    assert "dangerously-bypass" not in container.commands[0][-1]


def test_codex_uses_docker_isolated_fallback_only_for_bwrap_failure() -> None:
    container = FakeContainer([
        _result(0, "bwrap: No permissions to create a new namespace"),
        _result(0, "changed tests/test_target.py"),
    ])
    sandbox = DockerSandboxContainer(container, 60)

    execution = sandbox.run_codex("make a focused test", 30)

    assert execution.fallback is not None
    assert "--sandbox workspace-write" in container.commands[0][-1]
    assert "--dangerously-bypass-approvals-and-sandbox" in container.commands[1][-1]


# Verbatim from a recorded 2026-08-03 run whose Codex account was out of quota.
# The agent never started, so the empty diff it left behind is not evidence.
QUOTA_EXHAUSTED_OUTPUT = (
    "warning: Codex could not find bubblewrap on PATH. Codex will use the bundled bubblewrap "
    "in the meantime.\n"
    "ERROR: You've hit your usage limit. Upgrade to Plus to continue using Codex "
    "(https://chatgpt.com/explore/plus), or try again at Aug 8th, 2026 2:31 AM.\n"
)


def test_codex_quota_exhaustion_is_an_operational_failure_not_an_empty_diff() -> None:
    container = FakeContainer([_result(1, QUOTA_EXHAUSTED_OUTPUT)])
    sandbox = DockerSandboxContainer(container, 60)

    try:
        sandbox.run_codex("make a focused test", 30)
    except CodexAgentUnavailable as error:
        assert "no remaining usage quota" in str(error)
        assert error.execution.exit_code == 1
    else:
        raise AssertionError("an unusable Codex account must not return a normal execution")


def test_codex_rejected_credential_is_an_operational_failure() -> None:
    for output in ("Please run `codex login`", "invalid_api_key", "401 Unauthorized"):
        container = FakeContainer([_result(1, output)])
        sandbox = DockerSandboxContainer(container, 60)
        try:
            sandbox.run_codex("make a focused test", 30)
        except CodexAgentUnavailable:
            continue
        raise AssertionError(f"credential failure {output!r} must not return a normal execution")


def test_agent_failure_is_detected_after_the_bwrap_fallback_too() -> None:
    container = FakeContainer([
        _result(0, "bwrap: No permissions to create a new namespace"),
        _result(1, QUOTA_EXHAUSTED_OUTPUT),
    ])
    sandbox = DockerSandboxContainer(container, 60)

    try:
        sandbox.run_codex("make a focused test", 30)
    except CodexAgentUnavailable as error:
        assert "no remaining usage quota" in str(error)
    else:
        raise AssertionError("the fallback path must apply the same agent-availability check")


def test_normal_codex_output_is_never_treated_as_an_agent_failure() -> None:
    # A real investigation may legitimately discuss limits or auth in its notes.
    container = FakeContainer([
        _result(0, "Added a test asserting the rate limit error is raised when the API key is missing."),
    ])
    sandbox = DockerSandboxContainer(container, 60)

    execution = sandbox.run_codex("make a focused test", 30)

    assert execution.fallback is None


def test_codex_reports_clear_error_when_fallback_cannot_run() -> None:
    container = FakeContainer([
        _result(0, "bwrap: No permissions to create a new namespace"),
        _result(1, "bwrap: No permissions to create a new namespace"),
    ])
    sandbox = DockerSandboxContainer(container, 60)

    with pytest.raises(CodexSandboxUnavailable, match="Docker-isolated fallback"):
        sandbox.run_codex("make a focused test", 30)


def test_container_mounts_only_workspace_and_read_only_auth(tmp_path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    auth = tmp_path / "auth.json"
    auth.write_text("{}", encoding="utf-8")
    captured = {}

    class FakeContainers:
        def run(self, image_id, **kwargs):
            captured["image_id"] = image_id
            captured.update(kwargs)
            return FakeContainer([])

    docker_client = SimpleNamespace(containers=FakeContainers())
    DockerSandboxContainer.start(docker_client, SimpleNamespace(id="image-1"), repository, auth, 60, ContainerRole.AGENT)

    assert captured["volumes"] == {
        str(repository): {"bind": "/workspace/repo", "mode": "rw"},
        str(auth): {"bind": "/root/.codex/auth.json", "mode": "ro"},
    }
    assert "privileged" not in captured
    assert "userns_mode" not in captured


def test_test_role_cannot_invoke_codex() -> None:
    sandbox = DockerSandboxContainer(FakeContainer([]), 60, ContainerRole.TEST)
    with pytest.raises(RuntimeError, match="only in the agent container"):
        sandbox.run_codex("probe", 1)
