import pytest
from fastapi.testclient import TestClient

from app import compound_details
from app.main import app


def test_comparison_preserves_column_order(monkeypatch):
    properties = {"241": ("C6H6", "78.11"), "2244": ("C9H8O4", "180.16")}

    def fake_details(cid):
        formula, weight = properties[cid]
        return {
            "cid": int(cid),
            "molecular_formula": formula,
            "molecular_weight_g_mol": weight,
            "record_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
        }

    monkeypatch.setattr(compound_details, "fetch_compound_details", fake_details)
    with TestClient(app) as client:
        # Reverse the manual example to catch accidental sorting.
        response = client.get("/compare-compounds",
                              params={"left": "241", "right": "2244"})

    assert response.status_code == 200
    html = response.text
    assert html.index("PubChem CID 241</a>") < html.index("PubChem CID 2244</a>")
    assert html.index("<td>C6H6</td>") < html.index("<td>C9H8O4</td>")
    assert html.index("<td>78.11</td>") < html.index("<td>180.16</td>")


@pytest.mark.parametrize("right", ["aspirin", "2244"])
def test_invalid_pair_does_not_contact_pubchem(monkeypatch, right):
    def unexpected_lookup(cid):
        pytest.fail("Invalid input should not trigger a lookup.")

    monkeypatch.setattr(compound_details, "fetch_compound_details", unexpected_lookup)
    with TestClient(app) as client:
        response = client.get("/compare-compounds",
                              params={"left": "2244", "right": right})
    assert response.status_code == 400


def test_missing_second_compound_does_not_show_partial_table(monkeypatch):
    def fake_details(cid):
        if cid == "241":
            raise compound_details.CompoundNotFound("No record for CID 241.")
        return {"cid": 2244}

    monkeypatch.setattr(compound_details, "fetch_compound_details", fake_details)
    with TestClient(app) as client:
        response = client.get("/compare-compounds",
                              params={"left": "2244", "right": "241"})

    assert response.status_code == 404
    assert "No record for CID 241." in response.text
    assert "<table" not in response.text