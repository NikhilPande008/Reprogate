from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from time import monotonic, perf_counter

from triage.sandbox.artifacts import copy_artifact, write_container_file


@dataclass(frozen=True)
class ContainerCommandResult:
    exit_code: int
    output: str
    command: str = ""
    elapsed_ms: int = 0


@dataclass(frozen=True)
class CodexExecutionResult:
    result: ContainerCommandResult
    preferred: ContainerCommandResult
    fallback: ContainerCommandResult | None


class CodexSandboxUnavailable(RuntimeError):
    def __init__(self, preferred: ContainerCommandResult, fallback: ContainerCommandResult):
        super().__init__(
            "Codex could not create its workspace sandbox, and the Docker-isolated fallback "
            "also reported the user-namespace failure."
        )
        self.preferred = preferred
        self.fallback = fallback


class CodexAgentUnavailable(RuntimeError):
    """The agent never ran: credentials, quota, or entitlement blocked invocation.

    This must not reach the validator. An agent that could not start produces an
    empty diff, which is indistinguishable at the diff layer from an agent that
    ran and chose to change nothing — but the two mean opposite things. Treating
    the first as evidence would let an infrastructure fault be reported as a
    bounded finding about the repository.
    """

    def __init__(self, reason: str, execution: ContainerCommandResult):
        super().__init__(f"Codex could not be invoked: {reason}")
        self.reason = reason
        self.execution = execution


class SandboxTimeout(RuntimeError):
    pass


class ContainerRole(StrEnum):
    SETUP = "setup"
    AGENT = "agent"
    TEST = "test"


class DockerSandboxContainer:
    def __init__(self, container, overall_timeout_seconds: int, role: ContainerRole = ContainerRole.AGENT):
        self.container = container
        self.deadline = monotonic() + overall_timeout_seconds
        self.role = role

    @classmethod
    def start(cls, docker_client, image, repository_path: Path, auth_path: Path, overall_timeout_seconds: int, role: ContainerRole = ContainerRole.AGENT, network_policy: str = "allowed") -> "DockerSandboxContainer":
        volumes = {str(repository_path): {"bind": "/workspace/repo", "mode": "rw"}}
        if role is ContainerRole.AGENT and auth_path.is_file():
            volumes[str(auth_path)] = {"bind": "/root/.codex/auth.json", "mode": "ro"}
        # Docker does not inherit the host environment by default, but pass an
        # explicit empty environment so the role boundary is visible in
        # inspection and cannot accidentally grow through a wrapper default.
        kwargs = {"environment": {}}
        if network_policy == "isolated":
            kwargs["network_mode"] = "none"
        container = docker_client.containers.run(
            image.id,
            command=["tail", "-f", "/dev/null"],
            working_dir="/workspace/repo",
            volumes=volumes,
            detach=True,
            **kwargs,
        )
        return cls(container, overall_timeout_seconds, role)

    @property
    def id(self) -> str:
        return self.container.id

    def run(self, command: str, timeout_seconds: int) -> ContainerCommandResult:
        remaining = int(self.deadline - monotonic())
        if remaining <= 0:
            self.terminate()
            raise SandboxTimeout("Overall investigation timeout exceeded")
        timeout = min(timeout_seconds, remaining)
        started = perf_counter()
        result = self.container.exec_run(["sh", "-lc", f"timeout {timeout}s {command}"], demux=False)
        elapsed_ms = round((perf_counter() - started) * 1000)
        output = result.output.decode("utf-8", errors="replace") if isinstance(result.output, bytes) else result.output
        if result.exit_code == 124:
            self.terminate()
            raise SandboxTimeout(f"Command timed out after {timeout} seconds: {command}")
        return ContainerCommandResult(result.exit_code, output, command, elapsed_ms)

    def run_codex(self, prompt: str, timeout_seconds: int) -> CodexExecutionResult:
        """Run Codex with its normal sandbox, then use Docker isolation only if bwrap is unavailable."""
        if self.role is not ContainerRole.AGENT:
            raise RuntimeError("Codex may run only in the agent container")
        preferred = self.run(
            "codex exec --sandbox workspace-write --ephemeral " + _shell_quote(prompt),
            timeout_seconds,
        )
        if not _requires_docker_isolated_fallback(preferred.output):
            _reject_unavailable_agent(preferred)
            return CodexExecutionResult(preferred, preferred, None)

        fallback = self.run(
            "codex exec --dangerously-bypass-approvals-and-sandbox --ephemeral " + _shell_quote(prompt),
            timeout_seconds,
        )
        if _requires_docker_isolated_fallback(fallback.output):
            raise CodexSandboxUnavailable(preferred, fallback)
        _reject_unavailable_agent(fallback)
        return CodexExecutionResult(fallback, preferred, fallback)

    def write_artifact(self, path: str, content: str) -> None:
        parent = str(Path(path).parent)
        self.container.exec_run(["mkdir", "-p", parent])
        write_container_file(self.container, path, content)

    def copy_artifact(self, source: str, destination: Path) -> Path:
        return copy_artifact(self.container, source, destination)

    def commit(self):
        return self.container.commit()

    def terminate(self) -> None:
        try:
            self.container.kill()
        except Exception:
            pass

    def remove(self) -> None:
        self.container.remove(force=True)


def _requires_docker_isolated_fallback(output: str) -> bool:
    return "bwrap: No permissions to create a new namespace" in output


# Deliberately narrow. Each marker means the CLI refused to start work at all.
# A broader match risks reclassifying a real investigation as an outage, which
# would hide genuine evidence just as badly as the reverse.
_AGENT_UNAVAILABLE_MARKERS: tuple[tuple[str, str], ...] = (
    ("hit your usage limit", "the configured Codex account has no remaining usage quota"),
    ("Upgrade to Plus to continue using Codex", "the configured Codex account lacks the required entitlement"),
    ("Please run `codex login`", "no usable Codex credential is mounted"),
    ("Not logged in", "no usable Codex credential is mounted"),
    ("invalid_api_key", "the mounted Codex credential was rejected"),
    ("Incorrect API key provided", "the mounted Codex credential was rejected"),
    ("401 Unauthorized", "the mounted Codex credential was rejected"),
)


def _agent_unavailable_reason(output: str) -> str | None:
    for marker, reason in _AGENT_UNAVAILABLE_MARKERS:
        if marker in output:
            return reason
    return None


def _reject_unavailable_agent(execution: ContainerCommandResult) -> None:
    """Fail loudly when the agent never ran, instead of returning an empty diff."""
    reason = _agent_unavailable_reason(execution.output)
    if reason is not None:
        raise CodexAgentUnavailable(reason, execution)


def _shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"
