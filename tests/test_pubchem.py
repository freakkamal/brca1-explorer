"""Test compound lookup using simulated PubChem responses."""

import hashlib

import httpx
import pytest

from app import pubchem, storage


@pytest.fixture
def mock_pubchem(monkeypatch, tmp_path):
    # Keep test responses separate from the project's real evidence.
    monkeypatch.setattr(storage, "PROJECT_ROOT", tmp_path)

    def setup(expected_name, status, body):
        def fake_post(url, *, data, timeout):
            assert url == (
                "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/cids/JSON"
            )
            assert data == {"name": expected_name}
            return httpx.Response(
                status,
                content=body,
                request=httpx.Request("POST", url),
            )

        monkeypatch.setattr(pubchem.httpx, "post", fake_post)

    return setup


def test_lookup_saves_original_response(mock_pubchem, tmp_path):
    body = b'{"IdentifierList": {"CID": [2244]}}\n'
    mock_pubchem("aspirin", 200, body)

    result = pubchem.lookup_compound("aspirin")

    assert result["matches"] == [{
        "cid": 2244,
        "record_url": "https://pubchem.ncbi.nlm.nih.gov/compound/2244",
    }]
    digest = hashlib.sha256(body).hexdigest()
    assert result["response_sha256"] == digest
    assert result["raw_file"] == f"data/raw/pubchem/{digest}.json"
    assert (tmp_path / result["raw_file"]).read_bytes() == body


def test_unknown_name_is_reported(mock_pubchem, tmp_path):
    mock_pubchem("unknown-example", 404, b'{"Fault": {}}')

    with pytest.raises(ValueError, match="PubChem found no compound"):
        pubchem.lookup_compound("unknown-example")

    assert not list((tmp_path / "data/raw/pubchem").glob("*.json"))


def test_multiple_matches_are_preserved(mock_pubchem):
    # Synthetic IDs: this checks that the app doesn't pick just one match.
    mock_pubchem("example", 200, b'{"IdentifierList":{"CID":[101,202,101]}}')

    result = pubchem.lookup_compound("example")

    assert [match["cid"] for match in result["matches"]] == [101, 202]

def test_browser_lookup_shows_all_matching_links(mock_pubchem):
    from fastapi.testclient import TestClient
    from app.main import app

    mock_pubchem("example", 200, b'{"IdentifierList":{"CID":[101,202]}}')

    with TestClient(app) as client:
        response = client.get("/compounds", params={"name": "example"})

    assert response.status_code == 200
    assert "Matching compound IDs: 2" in response.text
    for cid in (101, 202):
        assert f'href="https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"' in response.text
    assert "Response SHA-256:" in response.text


def test_browser_lookup_unknown_name_keeps_search_form(mock_pubchem):
    from fastapi.testclient import TestClient
    from app.main import app

    mock_pubchem("unknown-example", 404, b'{"Fault":{}}')

    with TestClient(app) as client:
        response = client.get("/compounds", params={"name": "unknown-example"})

    assert response.status_code == 404
    assert "PubChem found no compound" in response.text
    assert 'name="name"' in response.text