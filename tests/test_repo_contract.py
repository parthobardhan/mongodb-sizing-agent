import importlib.util
import inspect
from pathlib import Path

import pytest

EXPECTED_METHODS = (
    "find_by_key",
    "find_detail_lines",
    "find_release",
    "count_by_status",
)


def _load_example_repository(example_case_dir: Path):
    path = example_case_dir / "outputs" / "mongo_repository.py"
    if not path.is_file():
        pytest.skip("missing outputs/mongo_repository.py in _example")
    spec = importlib.util.spec_from_file_location("example_mongo_repository", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_repository_defines_expected_methods(example_case_dir: Path):
    module = _load_example_repository(example_case_dir)
    repo_cls = module.ClaimDocumentRepository
    for name in EXPECTED_METHODS:
        assert hasattr(repo_cls, name)
        assert callable(getattr(repo_cls, name))


def test_example_repository_methods_have_legacy_sql_docstrings(example_case_dir: Path):
    module = _load_example_repository(example_case_dir)
    repo_cls = module.ClaimDocumentRepository
    for name in EXPECTED_METHODS:
        doc = inspect.getdoc(getattr(repo_cls, name)) or ""
        assert "Legacy SQL" in doc or "SELECT" in doc, f"{name} missing legacy SQL docstring"
