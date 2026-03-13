"""
Cowork compatibility tests for Phase 1: COWK-01, COWK-02.

COWK-01: Preflight import check -- clear error if packages are missing
COWK-02: requirements.txt contains openpyxl and pydantic; no python-dotenv
"""

import sys
import importlib
import pytest


# ---------------------------------------------------------------------------
# COWK-01: Preflight import check
# ---------------------------------------------------------------------------

def test_preflight_passes():
    """
    Importing the scripts package must succeed without SystemExit when all
    required packages are installed.
    """
    import scripts  # noqa: F401
    # If we reach here, no SystemExit was raised
    assert True


def test_preflight_fails_on_missing(monkeypatch, capsys):
    """
    When a required package is not importable, _preflight_check must print
    "[ERROR] Missing: {pip_name}" and raise SystemExit(1).
    """
    from scripts import _preflight_check, _REQUIRED_PACKAGES

    # Monkeypatch __builtins__.__import__ to raise ImportError for 'pandas'
    real_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

    def mock_import(name, *args, **kwargs):
        if name == 'pandas':
            raise ImportError(f"Mocked missing: {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr('builtins.__import__', mock_import)

    with pytest.raises(SystemExit) as exc_info:
        _preflight_check()

    assert exc_info.value.code == 1, "SystemExit code must be 1"
    out = capsys.readouterr().out
    assert '[ERROR] Missing: pandas' in out, (
        f"Expected '[ERROR] Missing: pandas' in output, got: {repr(out)}"
    )


# ---------------------------------------------------------------------------
# COWK-02: requirements.txt contents
# ---------------------------------------------------------------------------

def test_requirements_contents():
    """
    requirements.txt must contain openpyxl and pydantic entries, and must NOT
    contain python-dotenv.
    """
    from pathlib import Path

    req_path = Path(__file__).parent.parent / 'requirements.txt'
    assert req_path.exists(), f"requirements.txt not found at {req_path}"

    contents = req_path.read_text(encoding='utf-8')

    assert 'openpyxl' in contents, (
        "requirements.txt must contain 'openpyxl'"
    )
    assert 'pydantic' in contents, (
        "requirements.txt must contain 'pydantic'"
    )
    assert 'python-dotenv' not in contents, (
        "requirements.txt must NOT contain 'python-dotenv'"
    )
