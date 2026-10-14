"""Keep saved test responses in temporary directories."""
import pytest

from app import storage


@pytest.fixture(autouse=True)
def isolate_raw_response_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "PROJECT_ROOT", tmp_path)