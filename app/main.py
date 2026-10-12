"""Milestone 1: local service foundation; no scientific retrieval yet."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(
    title="BRCA1 Evidence Explorer",
    version="0.1.0",
    description=(
        "Local research prototype. Milestone 1 provides service health only. "
        "Scientific retrieval and AI summaries are not implemented. "
        "Not for clinical decisions."
    ),
)


class HealthResponse(BaseModel):
    status: Literal["ok"]


@app.get("/health", response_model=HealthResponse, tags=["Service"])
def health() -> HealthResponse:
    """Confirm the API responds, not external database or scientific validity."""
    return HealthResponse(status="ok")
