import json
import ast
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from triage.sandbox.manager import EnvironmentSetupFailure, SetupCommand


class RunnerSelectionError(EnvironmentSetupFailure):
    pass


class RunnerAdapter(Protocol):
    id: str
    output_artifact_kind: str
    def setup_command(self, repository_path: Path, configured_command: str | None) -> SetupCommand: ...
    def focused_command(self, status_output: str, structured_result_path: str | None = None) -> str: ...
    def is_test_path(self, path: Path) -> bool: ...
    def validate_output(self, output: str, exit_code: int): ...


@dataclass(frozen=True)
class FocusedTestSelection:
    runner_id: str
    targets: tuple[str, ...]
    source_paths: tuple[str, ...]
    precision: str  # EXACT, FILE_ONLY, UNAVAILABLE
    reason: str
    diagnostics: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {"runner_id": self.runner_id, "targets": list(self.targets), "source_paths": list(self.source_paths), "precision": self.precision, "reason": self.reason, "diagnostics": list(self.diagnostics)}


def _quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


@dataclass(frozen=True)
class PytestAdapter:
    id: str = "pytest"
    output_artifact_kind: str = "pytest_output"

    def setup_command(self, repository_path: Path, configured_command: str | None) -> SetupCommand:
        if configured_command:
            return SetupCommand(configured_command, "explicit SANDBOX_SETUP_COMMAND")
        if (repository_path / "requirements-dev.txt").is_file():
            return SetupCommand("uv pip install --system -r requirements-dev.txt", "requirements-dev.txt via pinned uv")
        if (repository_path / "requirements.txt").is_file():
            return SetupCommand("uv pip install --system -r requirements.txt", "requirements.txt via pinned uv")
        pyproject = _pyproject(repository_path)
        if pyproject is not None:
            groups = pyproject.get("dependency-groups", {})
            if isinstance(groups, dict):
                for group in ("dev", "test"):
                    if group in groups:
                        return SetupCommand(
                            f"uv pip install --system --group {group} -e .",
                            f"pyproject.toml dependency-groups.{group} via pinned uv",
                        )
            tool = pyproject.get("tool", {})
            if isinstance(tool, dict) and isinstance(tool.get("poetry"), dict):
                poetry_groups = tool["poetry"].get("group", {})
                with_dev = " --with dev" if isinstance(poetry_groups, dict) and "dev" in poetry_groups else ""
                return SetupCommand(
                    f"poetry config virtualenvs.create false && poetry install{with_dev} --no-interaction",
                    "pyproject.toml Poetry metadata via pinned Poetry",
                )
        for name in ("pyproject.toml", "setup.py", "setup.cfg"):
            if (repository_path / name).is_file():
                return SetupCommand("uv pip install --system -e .", f"Python packaging metadata ({name}) via pinned uv")
        raise EnvironmentSetupFailure("Environment setup unavailable for pytest: no supported Python dependency metadata found")

    def focused_command(self, status_output: str, structured_result_path: str | None = None) -> str:
        paths = _changed_paths(status_output, self.is_test_path)
        junit = f" --junitxml={_quote(structured_result_path)}" if structured_result_path else ""
        return "python -m pytest -q" + junit + (" " + " ".join(_quote(path) for path in paths) if paths else "")

    def select_targets(self, repository_path: Path, diff_text: str, status_output: str = "") -> FocusedTestSelection:
        exact = _pytest_nodes_from_diff(repository_path, diff_text, self.is_test_path)
        if exact:
            return FocusedTestSelection(self.id, tuple(exact), tuple(sorted({node.split("::")[0] for node in exact})), "EXACT", "Changed diff lines map to executable pytest test nodes.")
        paths = _diff_test_paths(diff_text, self.is_test_path) or _changed_paths(status_output, self.is_test_path)
        if paths:
            return FocusedTestSelection(self.id, tuple(paths), tuple(paths), "FILE_ONLY", "Changed test files could not be mapped safely to executable pytest test nodes.")
        return FocusedTestSelection(self.id, (), (), "UNAVAILABLE", "No changed executable pytest test target could be determined.")

    def command_for_selection(self, selection: FocusedTestSelection, structured_result_path: str | None = None) -> str:
        junit = f" --junitxml={_quote(structured_result_path)}" if structured_result_path else ""
        return "python -m pytest -q" + junit + (" " + " ".join(_quote(target) for target in selection.targets) if selection.targets else "")

    def is_test_path(self, path: Path) -> bool:
        return path.suffix == ".py" and (path.parts[0] == "tests" or path.name.startswith("test_"))

    def validate_output(self, output: str, exit_code: int):
        from triage.validation.pytest_parser import parse_pytest_output
        return parse_pytest_output(output, exit_code)


@dataclass(frozen=True)
class VitestAdapter:
    id: str = "vitest"
    output_artifact_kind: str = "vitest_output"

    def setup_command(self, repository_path: Path, configured_command: str | None) -> SetupCommand:
        if configured_command:
            return SetupCommand(configured_command, "explicit SANDBOX_SETUP_COMMAND")
        package = _package_json(repository_path)
        if package is None or not _has_vitest(package):
            raise EnvironmentSetupFailure("Environment setup unavailable for Vitest: package.json must declare vitest or set SANDBOX_SETUP_COMMAND")
        if (repository_path / "package-lock.json").is_file():
            return SetupCommand("npm ci", "package-lock.json with declared Vitest")
        # npm install is safe only for an explicitly declared Vitest project.
        return SetupCommand("npm install", "package.json with declared Vitest")

    def focused_command(self, status_output: str, structured_result_path: str | None = None) -> str:
        paths = _changed_paths(status_output, self.is_test_path)
        junit = f" --reporter=junit --outputFile={_quote(structured_result_path)}" if structured_result_path else ""
        return "npm exec -- vitest run" + junit + (" -- " + " ".join(_quote(path) for path in paths) if paths else "")

    def select_targets(self, repository_path: Path, diff_text: str, status_output: str = "") -> FocusedTestSelection:
        exact = _vitest_nodes_from_diff(repository_path, diff_text, self.is_test_path)
        if exact:
            return FocusedTestSelection(
                self.id,
                tuple(exact),
                tuple(sorted({node.split("::", 1)[0] for node in exact})),
                "EXACT",
                "Changed assertion lines map to static top-level Vitest test names.",
            )
        paths = _diff_test_paths(diff_text, self.is_test_path) or _changed_paths(status_output, self.is_test_path)
        return FocusedTestSelection(self.id, tuple(paths), tuple(paths), "FILE_ONLY" if paths else "UNAVAILABLE", "Vitest change is outside the conservative exact-selection subset; file selection is diagnostic-only." if paths else "No changed Vitest test file could be determined.")

    def command_for_selection(self, selection: FocusedTestSelection, structured_result_path: str | None = None) -> str:
        junit = f" --reporter=junit --outputFile={_quote(structured_result_path)}" if structured_result_path else ""
        if selection.precision == "EXACT":
            by_path: dict[str, list[str]] = {}
            for target in selection.targets:
                path, name = target.split("::", 1)
                by_path.setdefault(path, []).append(name)
            if len(by_path) == 1:
                path, names = next(iter(by_path.items()))
                pattern = "^(?:" + "|".join(re.escape(name) for name in names) + ")$"
                return "npm exec -- vitest run" + junit + " -t " + _quote(pattern) + " -- " + _quote(path)
            return "npm exec -- vitest run" + junit + " -- " + " ".join(_quote(path) for path in selection.source_paths)
        return "npm exec -- vitest run" + junit + (" -- " + " ".join(_quote(target) for target in selection.targets) if selection.targets else "")

    def is_test_path(self, path: Path) -> bool:
        return path.suffix in {".js", ".jsx", ".ts", ".tsx"} and (
            path.parts[0] in {"test", "tests", "__tests__"} or ".test." in path.name or ".spec." in path.name
        )

    def validate_output(self, output: str, exit_code: int):
        from triage.validation.vitest_parser import parse_vitest_output
        return parse_vitest_output(output, exit_code)


@dataclass(frozen=True)
class JestAdapter:
    """Manifest-aware Jest execution with deliberately non-confirming selection.

    Jest can run a changed test file safely, but this project does not yet have
    a sound, cross-language exact-test selector and structured-result mapping
    for Jest. Keeping the selection FILE_ONLY records useful setup and target
    diagnostics without becoming a behavior-gap confirmation.
    """

    id: str = "jest"
    output_artifact_kind: str = "jest_output"

    def setup_command(self, repository_path: Path, configured_command: str | None) -> SetupCommand:
        if configured_command:
            return SetupCommand(configured_command, "explicit SANDBOX_SETUP_COMMAND")
        package = _package_json(repository_path)
        if package is None or not _has_jest(package):
            raise EnvironmentSetupFailure(
                "Environment setup unavailable for Jest: package.json must declare jest or set SANDBOX_SETUP_COMMAND"
            )
        if (repository_path / "package-lock.json").is_file():
            return SetupCommand("npm ci", "package-lock.json with declared Jest")
        return SetupCommand("npm install", "package.json with declared Jest")

    def focused_command(self, status_output: str, structured_result_path: str | None = None) -> str:
        paths = _changed_paths(status_output, self.is_test_path)
        return "npm exec -- jest --ci" + (" --runTestsByPath " + " ".join(_quote(path) for path in paths) if paths else "")

    def select_targets(self, repository_path: Path, diff_text: str, status_output: str = "") -> FocusedTestSelection:
        paths = _diff_test_paths(diff_text, self.is_test_path) or _changed_paths(status_output, self.is_test_path)
        return FocusedTestSelection(
            self.id,
            tuple(paths),
            tuple(paths),
            "FILE_ONLY" if paths else "UNAVAILABLE",
            "Jest exact test-name selection and JUnit mapping are not implemented; file selection is diagnostic-only."
            if paths else "No changed Jest test file could be determined.",
            ("Operator remediation: use pytest for confirmation, or configure a supported runner while Jest exact selection remains unavailable.",)
            if paths else (),
        )

    def command_for_selection(self, selection: FocusedTestSelection, structured_result_path: str | None = None) -> str:
        return "npm exec -- jest --ci" + (" --runTestsByPath " + " ".join(_quote(target) for target in selection.targets) if selection.targets else "")

    def is_test_path(self, path: Path) -> bool:
        return path.suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"} and (
            path.parts[0] in {"test", "tests", "__tests__"} or ".test." in path.name or ".spec." in path.name
        )

    def validate_output(self, output: str, exit_code: int):
        # Jest is not a confirmation-capable runner yet; the deterministic
        # validator rejects its FILE_ONLY selection before execution evidence.
        return None


def _changed_paths(status_output: str, predicate: Callable[[Path], bool]) -> list[str]:
    result: list[str] = []
    for line in status_output.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].split(" -> ")[-1]
        candidate = Path(path)
        if not candidate.is_absolute() and ".." not in candidate.parts and predicate(candidate):
            result.append(path)
    return result


def _diff_test_paths(diff_text: str, predicate: Callable[[Path], bool]) -> list[str]:
    paths: list[str] = []
    for raw in diff_text.splitlines():
        match = re.match(r"^\+\+\+ b/(.+)$", raw)
        if match:
            candidate = Path(match.group(1))
            if ".." not in candidate.parts and predicate(candidate): paths.append(str(candidate))
    return paths


def _pytest_nodes_from_diff(repository_path: Path, diff_text: str, predicate: Callable[[Path], bool]) -> list[str]:
    result: list[str] = []
    current: Path | None = None; changed: set[int] = set(); new_line: int | None = None
    for raw in diff_text.splitlines():
        path = re.match(r"^\+\+\+ b/(.+)$", raw)
        if path:
            current = Path(path.group(1)); changed = set(); new_line = None; continue
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if hunk: new_line = int(hunk.group(1)); continue
        if current is None or new_line is None: continue
        if raw.startswith("+") and not raw.startswith("+++"): changed.add(new_line); new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"): continue
        else: new_line += 1
        if not changed or not predicate(current): continue
        try: tree = ast.parse((repository_path / current).read_text(encoding="utf-8"))
        except (OSError, SyntaxError): continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_") and _body_changed(node, changed): result.append(f"{current}::{node.name}")
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for method in node.body:
                    if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)) and method.name.startswith("test_") and _body_changed(method, changed): result.append(f"{current}::{node.name}::{method.name}")
    return sorted(set(result))


def _body_changed(node: ast.AST, changed: set[int]) -> bool:
    start = getattr(node, "lineno", 0); end = getattr(node, "end_lineno", start)
    # Exclude a change solely on the def/decorator line: only changed executable body lines count.
    return any(start < line <= end for line in changed)


_VITEST_TOP_LEVEL = re.compile(r"^(?:export\s+)?(?:it|test)(?:\.(?:only|skip))?\s*\(\s*(['\"])([^'\"\\]+)\1")


def _vitest_nodes_from_diff(repository_path: Path, diff_text: str, predicate: Callable[[Path], bool]) -> list[str]:
    """Find only unambiguous static top-level Vitest assertions.

    Nested suites, parameterized tests, templates, and declaration-only changes
    intentionally remain FILE_ONLY. This accepted subset can be selected exactly
    and matched against a JUnit testcase without guessing.
    """
    changed_by_path: dict[Path, set[int]] = {}
    current: Path | None = None
    new_line: int | None = None
    for raw in diff_text.splitlines():
        path = re.match(r"^\+\+\+ b/(.+)$", raw)
        if path:
            current, new_line = Path(path.group(1)), None
            changed_by_path.setdefault(current, set())
            continue
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", raw)
        if hunk:
            new_line = int(hunk.group(1))
            continue
        if current is None or new_line is None:
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            changed_by_path[current].add(new_line)
            new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        else:
            new_line += 1
    targets: list[str] = []
    for path, changed in changed_by_path.items():
        if not predicate(path):
            continue
        try:
            lines = (repository_path / path).read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        declarations = [(index, match.group(2)) for index, line in enumerate(lines, start=1) if (match := _VITEST_TOP_LEVEL.match(line))]
        names = [name for _, name in declarations]
        if len(names) != len(set(names)):
            continue
        for offset, (start, name) in enumerate(declarations):
            end = declarations[offset + 1][0] if offset + 1 < len(declarations) else len(lines) + 1
            body_changes = [line_number for line_number in changed if start < line_number < end]
            if any(re.search(r"\b(?:expect|assert)\s*\(", lines[line_number - 1]) for line_number in body_changes):
                targets.append(f"{path}::{name}")
    return sorted(set(targets))


def _package_json(path: Path) -> dict | None:
    try:
        data = json.loads((path / "package.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _pyproject(path: Path) -> dict | None:
    try:
        data = tomllib.loads((path / "pyproject.toml").read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _has_vitest(package: dict) -> bool:
    return "vitest" in package.get("devDependencies", {}) or "vitest" in package.get("dependencies", {})


def _has_jest(package: dict) -> bool:
    return "jest" in package.get("devDependencies", {}) or "jest" in package.get("dependencies", {})


@dataclass(frozen=True)
class RunnerCapability:
    """Declared confirmation capability for one adapter.

    Kept beside the adapters so the published matrix cannot drift away from the
    selector that actually runs. `confirmation_capable` means only that this
    runner can reach `BEHAVIOR_GAP_CONFIRMED` when every deterministic gate
    passes; it is never a claim about a specific investigation.
    """

    runner_id: str
    implemented: bool
    confirmation_capable: bool
    selection_precision: str
    structured_results: str
    summary: str
    constraint: str


RUNNER_CAPABILITIES: tuple[RunnerCapability, ...] = (
    RunnerCapability(
        "pytest", True, True, "EXACT",
        "JUnit XML required for validation",
        "Default runner. AST-derived exact changed-test nodes map to matching JUnit testcases.",
        "Requires a resolvable setup command; PEP 735 dependency groups may need SANDBOX_SETUP_COMMAND.",
    ),
    RunnerCapability(
        "vitest", True, True, "EXACT for a conservative static top-level subset",
        "JUnit reporter required for validation",
        "Confirmation-capable only when changed assertion lines map to static top-level test names.",
        "Nested, parameterized, dynamic, or otherwise ambiguous tests fall back to FILE_ONLY and stay diagnostic-only.",
    ),
    RunnerCapability(
        "jest", True, False, "FILE_ONLY",
        "Not mapped to structured validation",
        "Runs and records setup and target diagnostics, but cannot reach a behavior-gap confirmation.",
        "Exact test-name selection and trustworthy JUnit mapping are not implemented; selection stays FILE_ONLY by design.",
    ),
    RunnerCapability(
        "cargo", False, False, "UNAVAILABLE", "Not implemented",
        "Not implemented. Selecting it fails rather than guessing.", "Future adapter target.",
    ),
    RunnerCapability(
        "go", False, False, "UNAVAILABLE", "Not implemented",
        "Not implemented. Selecting it fails rather than guessing.", "Future adapter target.",
    ),
    RunnerCapability(
        "junit-java", False, False, "UNAVAILABLE", "Not implemented",
        "Not implemented. Selecting it fails rather than guessing.", "Future adapter target.",
    ),
    RunnerCapability(
        "rspec", False, False, "UNAVAILABLE", "Not implemented",
        "Not implemented. Selecting it fails rather than guessing.", "Future adapter target.",
    ),
)


def runner_capabilities() -> list[dict[str, object]]:
    """Return the declared capability matrix as serializable records."""
    return [
        {
            "runner_id": item.runner_id,
            "implemented": item.implemented,
            "confirmation_capable": item.confirmation_capable,
            "selection_precision": item.selection_precision,
            "structured_results": item.structured_results,
            "summary": item.summary,
            "constraint": item.constraint,
        }
        for item in RUNNER_CAPABILITIES
    ]


def select_runner(configured: str, repository_path: Path | None = None) -> RunnerAdapter:
    adapters = {"pytest": PytestAdapter(), "vitest": VitestAdapter(), "jest": JestAdapter()}
    if configured in adapters:
        return adapters[configured]
    if configured != "auto":
        raise RunnerSelectionError(f"Unsupported test runner {configured!r}; supported runners are pytest and vitest")
    if repository_path is None:
        raise RunnerSelectionError("Automatic runner selection requires a repository path")
    candidates = []
    if any((repository_path / name).is_file() for name in ("requirements.txt", "requirements-dev.txt", "pyproject.toml", "setup.py", "setup.cfg")):
        candidates.append(adapters["pytest"])
    if _has_vitest(_package_json(repository_path) or {}):
        candidates.append(adapters["vitest"])
    if _has_jest(_package_json(repository_path) or {}):
        candidates.append(adapters["jest"])
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise RunnerSelectionError("Unsupported repository: automatic selection found neither Python/pytest metadata nor a declared Vitest or Jest dependency")
    raise RunnerSelectionError("Ambiguous repository: automatic selection found multiple supported test frameworks; set TRIAGE_TEST_RUNNER explicitly")
