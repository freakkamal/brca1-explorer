"""Download matches from a saved BRCA1 literature bundle."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.mentions import find_mentions


router = APIRouter()


@router.get("/download-literature-mentions", tags=["Local viewer"])
def download_literature_mentions(bundle: str, q: str):
    """Export the same literal matches used by the literature viewer."""
    query = q.strip()

    try:
        result = find_mentions(bundle, query)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail="Bundle or referenced evidence file is missing."
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return JSONResponse(
        content={
            "query": query,
            "bundle_filename": result["filename"],
            "bundle_sha256": result["sha256"],
            "articles_searched": result["article_count"],
            "articles_matched": len(result["matches"]),
            "matches": result["matches"],
        },
        headers={
            "Content-Disposition": 'attachment; filename="brca1-literature-mentions.json"',
            "Cache-Control": "no-store",
        },
    )