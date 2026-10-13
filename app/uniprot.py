"""Retrieve and validate the human BRCA1 protein record."""

from datetime import datetime, timezone
import hashlib

import httpx


API_URL = "https://rest.uniprot.org/uniprotkb/P38398.json"
RECORD_URL = "https://www.uniprot.org/uniprotkb/P38398/entry"


def fetch_brca1_protein():
    """Return source-labelled identity data, or an explicit error."""
    try:
        response = httpx.get(API_URL, timeout=30)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise RuntimeError("UniProt timed out. Try again later.") from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"UniProt returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Could not connect to UniProt.") from exc

    retrieved_at = datetime.now(timezone.utc).isoformat()

    try:
        data = response.json()
        accession = data["primaryAccession"]
        organism = data["organism"]["scientificName"]
        taxonomy_id = data["organism"]["taxonId"]
        genes = [item["geneName"]["value"] for item in data["genes"]]

        if (
            accession != "P38398"
            or taxonomy_id != 9606
            or "BRCA1" not in genes
        ):
            raise ValueError("Unexpected protein identity.")
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(
            "UniProt returned an invalid or unexpected record."
        ) from exc

    return {
        "evidence_type": "retrieved",
        "source": "UniProt",
        "accession": accession,
        "gene": "BRCA1",
        "organism": organism,
        "taxonomy_id": taxonomy_id,
        "record_url": RECORD_URL,
        "api_url": API_URL,
        "retrieved_at_utc": retrieved_at,
        "response_sha256": hashlib.sha256(response.content).hexdigest(),
    }