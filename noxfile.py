"""
Nox configuration for multi-version Python testing.

Usage:
    nox                     Run tests on all Python versions (3.11, 3.12, 3.13)
    nox -s tests-3.12       Run tests on specific Python version
    nox -- -x               Pass arguments to pytest (e.g., stop on first failure)
    nox -- -k "test_name"   Run specific test
"""

import nox

nox.options.default_venv_backend = "uv"


@nox.session(python=["3.11", "3.12", "3.13"])
def tests(session: nox.Session) -> None:
    """Run unit tests across Python versions."""
    session.install("-e", ".")
    session.install("pytest", "pytest-cov", "pytest-random-order")
    session.run("pytest", "tests/unit/", *session.posargs)
