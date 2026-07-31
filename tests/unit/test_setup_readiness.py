from triage.setup_readiness import report


def test_offline_setup_readiness_reports_manifest_support_without_execution(tmp_path) -> None:
    python_repo = tmp_path / "python"; python_repo.mkdir(); (python_repo / "requirements.txt").write_text("pytest\n", encoding="utf-8")
    unsupported = tmp_path / "unsupported"; unsupported.mkdir()
    result = report([python_repo, unsupported])
    assert result["counts"] == {"ready": 1, "unsupported": 1}
    assert result["items"][0]["setup_command"] == "uv pip install --system -r requirements.txt"
    assert "must not be reported" in result["caveats"][1]


def test_setup_profile_fixture_matrix_reports_supported_profiles_and_negative_case(tmp_path) -> None:
    profiles = {
        "requirements": {"requirements.txt": "pytest\n"},
        "requirements-dev": {"requirements-dev.txt": "pytest\n", "requirements.txt": "pytest\n"},
        "dependency-groups-dev": {"pyproject.toml": "[dependency-groups]\ndev = ['pytest']\n"},
        "dependency-groups-test": {"pyproject.toml": "[dependency-groups]\ntest = ['pytest']\n"},
        "poetry": {"pyproject.toml": "[tool.poetry]\nname = 'fixture'\nversion = '0.1.0'\n[tool.poetry.group.dev]\n"},
        "editable": {"setup.py": "from setuptools import setup\nsetup()\n"},
        "unsupported": {},
    }
    paths = []
    for name, files in profiles.items():
        path = tmp_path / name; path.mkdir(); paths.append(path)
        for filename, content in files.items():
            (path / filename).write_text(content, encoding="utf-8")
    result = report(paths)
    assert result["counts"] == {"ready": 6, "unsupported": 1}
    commands = {item["path"].rsplit("/", 1)[-1]: item.get("setup_command") for item in result["items"]}
    assert commands["requirements"] == "uv pip install --system -r requirements.txt"
    assert commands["requirements-dev"] == "uv pip install --system -r requirements-dev.txt"
    assert commands["dependency-groups-dev"] == "uv pip install --system --group dev -e ."
    assert commands["dependency-groups-test"] == "uv pip install --system --group test -e ."
    assert commands["poetry"] == "poetry config virtualenvs.create false && poetry install --with dev --no-interaction"
    assert commands["editable"] == "uv pip install --system -e ."
