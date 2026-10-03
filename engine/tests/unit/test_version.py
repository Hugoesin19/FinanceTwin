"""F0 smoke: package is importable and versioned."""

from financetwin_engine import ENGINE_VERSION, __version__


def test_version() -> None:
    assert __version__ == "0.1.0"
    assert ENGINE_VERSION == "0.1.0"
    assert __version__ == ENGINE_VERSION
