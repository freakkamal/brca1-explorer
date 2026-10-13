"""Retrieve and validate the human BRCA1 gene record."""

from datetime import datetime, timezone
import hashlib

import httpx


API_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
RECORD_URL = "https://www.ncbi.nlm.nih.gov/gene/672"


def fetch_brca1_gene():
    """Return source-labelled gene identity, or an explicit error."""
    try:
        response = httpx.get(
            API_URL,
            params={
                "db": "gene",
                "id": "672",
                "retmode": "json",
                "tool": "brca1_evidence_explorer",
            },
            timeout=30,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise RuntimeError("NCBI timed out. Try again later.") from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"NCBI returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Could not connect to NCBI.") from exc

    retrieved_at = datetime.now(timezone.utc).isoformat()

    try:
        payload = response.json()
        if "error" in payload:
            raise ValueError("NCBI reported an error.")

        data = payload["result"]["672"]
        if "error" in data:
            raise ValueError("NCBI reported a record error.")

        gene_id = str(data["uid"])
        gene = data["name"]
        organism = data["organism"]["scientificname"]
        taxonomy_id = data["organism"]["taxid"]

        if (
            gene_id != "672"
            or gene != "BRCA1"
            or taxonomy_id != 9606
            or organism != "Homo sapiens"
        ):
            raise ValueError("Unexpected gene identity.")
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(
            "NCBI returned an invalid or unexpected record."
        ) from exc

    return {
        "evidence_type": "retrieved",
        "source": "NCBI Gene",
        "gene_id": gene_id,
        "gene": gene,
        "organism": organism,
        "taxonomy_id": taxonomy_id,
        "record_url": RECORD_URL,
        "api_url": str(response.request.url),
        "retrieved_at_utc": retrieved_at,
        "response_sha256": hashlib.sha256(response.content).hexdigest(),
    }