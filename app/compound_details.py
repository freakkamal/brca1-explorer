"""Retrieve molecular formula and molecular weight for an exact PubChem CID."""

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import re

import httpx

from app.storage import save_raw_response


class CompoundNotFound(ValueError):
    """PubChem did not find the requested CID."""


def fetch_compound_details(cid):
    cid_text = str(cid).strip()
    if not re.fullmatch(r"[1-9][0-9]*", cid_text):
        raise ValueError("Enter a positive whole-number CID, such as 2244.")

    url = (
        f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid_text}"
        "/property/MolecularFormula,MolecularWeight/JSON"
    )

    try:
        response = httpx.get(url, timeout=30)
        if response.status_code == 404:
            raise CompoundNotFound(f"PubChem found no compound for CID {cid_text}.")
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"PubChem returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Could not reach PubChem. Try again later.") from exc

    try:
        rows = response.json()["PropertyTable"]["Properties"]
        if not isinstance(rows, list) or len(rows) != 1:
            raise ValueError
        row = rows[0]
        if not isinstance(row, dict):
            raise ValueError
        if type(row.get("CID")) is not int or str(row["CID"]) != cid_text:
            raise RuntimeError("PubChem returned a different or missing CID.")

        formula = row["MolecularFormula"]
        if not isinstance(formula, str) or not formula.strip():
            raise ValueError

        weight_text = str(row["MolecularWeight"]).strip()
        weight = Decimal(weight_text)
        if not weight.is_finite() or weight <= 0:
            raise ValueError
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise RuntimeError(
            "PubChem returned missing or invalid compound properties."
        ) from exc

    saved = save_raw_response("pubchem", response.content)
    return {
        "source": "PubChem",
        "cid": row["CID"],
        "molecular_formula": formula.strip(),
        "molecular_weight_g_mol": weight_text,
        "record_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid_text}",
        "api_url": url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_file": saved["path"],
        "response_sha256": saved["sha256"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cid", help="PubChem compound ID, for example 2244.")
    args = parser.parse_args()
    try:
        result = fetch_compound_details(args.cid)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Compound lookup failed: {exc}\n")
    print(json.dumps(result, indent=2))