"""BRCA1 Evidence Explorer research backend."""

from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from app import ncbi, pubmed, uniprot


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
class GeneResponse(BaseModel):
    evidence_type: Literal["retrieved"]
    source: Literal["NCBI Gene"]
    gene_id: Literal["672"]
    gene: Literal["BRCA1"]
    organism: Literal["Homo sapiens"]
    taxonomy_id: Literal[9606]
    record_url: HttpUrl
    api_url: HttpUrl
    retrieved_at_utc: datetime
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


@app.get(
    "/genes/brca1",
    response_model=GeneResponse,
    tags=["Gene evidence"],
    responses={502: {"description": "NCBI retrieval failed"}},
)
def brca1_gene():
    """Retrieve validated human BRCA1 gene identity from NCBI."""
    try:
        return ncbi.fetch_brca1_gene()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
class LiteratureArticle(BaseModel):
    evidence_type: Literal["retrieved"]
    source: Literal["PubMed"]
    pmid: str = Field(pattern=r"^[1-9][0-9]*$")
    title: str = Field(min_length=1)
    abstract: str | None
    abstract_available: bool
    record_url: HttpUrl


class SearchProvenance(BaseModel):
    api_url: HttpUrl
    retrieved_at_utc: datetime
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FetchProvenance(BaseModel):
    # These values are null when no articles require fetching.
    api_url: HttpUrl | None
    retrieved_at_utc: datetime | None
    response_sha256: str | None = Field(
        pattern=r"^[0-9a-f]{64}$"
    )


class LiteratureResponse(BaseModel):
    evidence_type: Literal["retrieved"]
    source: Literal["PubMed"]
    query: str
    sort: Literal["relevance"]
    total_matching_records: int = Field(ge=0)
    returned_count: int = Field(ge=0, le=10)
    articles: list[LiteratureArticle] = Field(max_length=10)
    search_provenance: SearchProvenance
    fetch_provenance: FetchProvenance


@app.get(
    "/literature/brca1",
    response_model=LiteratureResponse,
    tags=["Literature evidence"],
    responses={502: {"description": "PubMed retrieval failed"}},
)
def brca1_literature():
    """Retrieve up to 10 BRCA1 articles with source metadata."""
    try:
        return pubmed.fetch_brca1_literature()
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc