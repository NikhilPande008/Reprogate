import json

import pytest

from triage.runners import RunnerSelectionError, select_runner


def test_explicit_runner_selection_wins_over_repository_metadata(tmp_path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"vitest": "1"}}))
    (tmp_path / "pyproject.toml").write_text("[project]\nname='both'")
    assert select_runner("vitest", tmp_path).id == "vitest"


def test_auto_runner_rejects_ambiguous_or_unsupported_repository(tmp_path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"vitest": "1"}}))
    (tmp_path / "pyproject.toml").write_text("[project]\nname='both'")
    with pytest.raises(RunnerSelectionError, match="Ambiguous"):
        select_runner("auto", tmp_path)
    with pytest.raises(RunnerSelectionError, match="Unsupported repository"):
        select_runner("auto", tmp_path / "empty")


def test_vitest_setup_and_focused_command_are_safe(tmp_path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"vitest": "1"}}))
    (tmp_path / "package-lock.json").write_text("{}")
    runner = select_runner("vitest", tmp_path)
    assert runner.setup_command(tmp_path, None).command == "npm ci"
    command = runner.focused_command(" M tests/a test.spec.ts\n M package.json\n")
    assert command == "npm exec -- vitest run -- 'tests/a test.spec.ts'"


def test_runners_emit_safe_junit_result_paths(tmp_path) -> None:
    pytest_runner = select_runner("pytest", tmp_path)
    assert "--junitxml='/tmp/result.xml'" in pytest_runner.focused_command(" M tests/test_a.py\n", "/tmp/result.xml")
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"vitest": "1"}}))
    vitest_runner = select_runner("vitest", tmp_path)
    command = vitest_runner.focused_command(" M tests/a.spec.ts\n", "/tmp/result.xml")
    assert "--reporter=junit --outputFile='/tmp/result.xml'" in command


def test_jest_setup_and_selection_remain_diagnostic_only(tmp_path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"devDependencies": {"jest": "29"}}))
    (tmp_path / "package-lock.json").write_text("{}")
    runner = select_runner("jest", tmp_path)
    assert runner.setup_command(tmp_path, None).command == "npm ci"
    selection = runner.select_targets(tmp_path, "+++ b/tests/widget.test.ts\n")
    assert selection.precision == "FILE_ONLY"
    assert selection.targets == ("tests/widget.test.ts",)
    assert "jest --ci --runTestsByPath 'tests/widget.test.ts'" in runner.command_for_selection(selection)


def test_auto_runner_selects_declared_jest(tmp_path) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": {"jest": "29"}}))
    assert select_runner("auto", tmp_path).id == "jest"


def test_pytest_setup_uses_pinned_toolchain_profiles(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text("[dependency-groups]\ndev = ['pytest']\n", encoding="utf-8")
    runner = select_runner("pytest", tmp_path)
    setup = runner.setup_command(tmp_path, None)
    assert setup.command == "uv pip install --system --group dev -e ."
    assert setup.reason == "pyproject.toml dependency-groups.dev via pinned uv"

    poetry = tmp_path / "poetry"
    poetry.mkdir()
    (poetry / "pyproject.toml").write_text("[tool.poetry]\nname = 'example'\nversion = '0.1.0'\n[tool.poetry.group.dev]\noptional = false\n", encoding="utf-8")
    poetry_setup = select_runner("pytest", poetry).setup_command(poetry, None)
    assert poetry_setup.command == "poetry config virtualenvs.create false && poetry install --with dev --no-interaction"
