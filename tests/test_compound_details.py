import hashlib

import httpx
import pytest
from fastapi.testclient import TestClient

from app import compound_details, storage
from app.main import app


@pytest.fixture
def reply(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "PROJECT_ROOT", tmp_path)

    def setup(status, rows):
        def fake_get(url, *, timeout):
            assert "/cid/2244/property/MolecularFormula,MolecularWeight/JSON" in url
            return httpx.Response(
                status,
                json={"PropertyTable": {"Properties": rows}},
                request=httpx.Request("GET", url),
            )
        monkeypatch.setattr(compound_details.httpx, "get", fake_get)

    return setup


def test_properties_are_saved_and_displayed(reply, tmp_path):
    reply(200, [{"CID": 2244, "MolecularFormula": "C9H8O4",
                 "MolecularWeight": "180.16"}])

    result = compound_details.fetch_compound_details("2244")
    raw = (tmp_path / result["raw_file"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == result["response_sha256"]

    with TestClient(app) as client:
        response = client.get("/compounds/2244")
    assert response.status_code == 200
    assert "C9H8O4" in response.text
    assert "180.16 g/mol" in response.text


def test_unknown_cid_returns_404(reply):
    reply(404, [])
    with TestClient(app) as client:
        assert client.get("/compounds/2244").status_code == 404


@pytest.mark.parametrize("row", [
    {"CID": 2244, "MolecularFormula": "C9H8O4"},
    {"CID": 999, "MolecularFormula": "C9H8O4", "MolecularWeight": "180.16"},
])
def test_incomplete_or_mismatched_record_is_not_saved(reply, tmp_path, row):
    reply(200, [row])
    with TestClient(app) as client:
        response = client.get("/compounds/2244")
    assert response.status_code == 502
    assert not list((tmp_path / "data/raw/pubchem").glob("*.json"))