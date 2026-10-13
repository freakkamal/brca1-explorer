"""BRCA1 Evidence Explorer research backend."""

from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from app import uniprot


app = FastAPI(
    title="BRCA1 Evidence Explorer",
    version="0.2.0",
    description=(
        "Research prototype providing human BRCA1 protein identity "
        "retrieved from UniProt. Not for clinical decisions."
    ),
)


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ProteinResponse(BaseModel):
    evidence_type: Literal["retrieved"]
    source: Literal["UniProt"]
    accession: Literal["P38398"]
    gene: Literal["BRCA1"]
    organism: str
    taxonomy_id: Literal[9606]
    record_url: HttpUrl
    api_url: HttpUrl
    retrieved_at_utc: datetime
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


@app.get("/health", response_model=HealthResponse, tags=["Service"])
def health() -> HealthResponse:
    """Check whether this API responds."""
    return HealthResponse(status="ok")


@app.get(
    "/proteins/brca1",
    response_model=ProteinResponse,
    tags=["Protein evidence"],
    responses={502: {"description": "UniProt retrieval failed"}},
)
def brca1_protein():
    """Retrieve validated human BRCA1 identity from UniProt."""
    try:
        return uniprot.fetch_brca1_protein()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc