"""Look up a compound name in PubChem and save the source response."""

import argparse
import json
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.storage import save_raw_response


def lookup_compound(name):
    name = name.strip()
    if not name:
        raise ValueError("Enter a compound name.")

    # Send the name as form data so punctuation is not part of the URL.
    api_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/cids/JSON"
    try:
        response = httpx.post(api_url, data={"name": name}, timeout=30)
        if response.status_code == 404:
            raise ValueError(f"PubChem found no compound for: {name}")
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise RuntimeError("PubChem timed out. Try again later.") from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"PubChem returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Could not connect to PubChem.") from exc

    try:
        cids = response.json()["IdentifierList"]["CID"]
        if not isinstance(cids, list) or not cids:
            raise ValueError
        if any(type(cid) is not int or cid <= 0 for cid in cids):
            raise ValueError
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("PubChem returned an unexpected response.") from exc

    saved = save_raw_response("pubchem", response.content)
    return {
        "source": "PubChem",
        "query_name": name,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "lookup_url": (
            "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"
            + quote(name, safe="") + "/cids/JSON"
        ),
        "matches": [
            {
                "cid": cid,
                "record_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
            }
            for cid in dict.fromkeys(cids)
        ],
        "raw_file": saved["path"],
        "response_sha256": saved["sha256"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Look up a PubChem compound.")
    parser.add_argument("name", help='Compound name, for example "aspirin".')
    args = parser.parse_args()
    try:
        result = lookup_compound(args.name)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, f"Lookup failed: {exc}\n")
    print(json.dumps(result, indent=2))