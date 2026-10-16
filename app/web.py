"""Local browser viewer for saved BRCA1 evidence."""

import json
from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app import report, storage


router = APIRouter()


def text(value):
    """Escape evidence text before placing it in HTML."""
    return escape(str(value), quote=True)


def page(body, status_code=200):
    """Wrap content in a readable, self-contained page."""
    html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>BRCA1 Evidence Explorer</title>
<style>
body {
    margin: 0;
    background: #f3f6fa;
    color: #18283b;
    font-family: system-ui, sans-serif;
    line-height: 1.65;
}
main {
    max-width: 960px;
    margin: auto;
    padding: 32px 20px;
}
h1, h2, h3 { line-height: 1.3; }
section, article {
    background: white;
    padding: 24px;
    margin: 20px 0;
    border: 1px solid #dce3ec;
    border-radius: 12px;
}
a { color: #075bb5; }
.abstract { white-space: pre-wrap; }
.notice {
    background: #e7effb;
    padding: 16px;
    border-radius: 8px;
}
.meta { color: #465a70; overflow-wrap: anywhere; }
select {
    display: block;
    width: 100%;
    margin: 8px 0 16px;
    padding: 10px;
    font: inherit;
}
button {
    padding: 10px 18px;
    border: 0;
    border-radius: 6px;
    background: #075bb5;
    color: white;
    font: inherit;
    cursor: pointer;
}
</style>
</head>
<body>
<main>
<h1>BRCA1 Evidence Explorer</h1>
<p class="notice">
Research use only. Not for clinical decisions.
This page displays saved evidence, not an AI-generated summary.
</p>
""" + body + """
</main>
</body>
</html>
"""
    return HTMLResponse(
        content=html,
        status_code=status_code,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/", response_class=HTMLResponse, tags=["Local viewer"])
def home(bundle: str | None = None):
    """Display a selected bundle, or the latest one by default."""
    try:
        bundle_directory = storage.PROJECT_ROOT / "data" / "bundles"
        candidates = [
            path
            for path in bundle_directory.glob("brca1-*.json")
            if path.is_file()
        ]

        if not candidates and bundle is None:
            return page(
                "<section><h2>No saved bundles yet</h2>"
                "<p>Create an evidence bundle from Command Prompt:</p>"
                "<pre>.venv\\Scripts\\python.exe -m app.evidence</pre>"
                "<p>Then refresh this page.</p></section>"
            )

        candidates.sort(
            key=lambda path: (path.stat().st_mtime_ns, path.name),
            reverse=True,
        )
        available = {path.name: path for path in candidates}

        if bundle is None:
            bundle_path = candidates[0]
        elif bundle in available:
            bundle_path = available[bundle]
        else:
            return page(
                "<section><h2>Bundle not found</h2>"
                "<p>The requested bundle is not available.</p>"
                '<p><a href="/">Return to the latest bundle</a></p>'
                "</section>",
                status_code=404,
            )

        options = []
        for candidate in candidates:
            selected = (
                " selected" if candidate == bundle_path else ""
            )
            options.append(
                f'<option value="{text(candidate.name)}"{selected}>'
                f"{text(candidate.name)}</option>"
            )

        selector = (
            "<section><h2>Choose an evidence bundle</h2>"
            '<form action="/" method="get">'
            '<label for="bundle">Saved bundle</label>'
            '<select id="bundle" name="bundle">'
            + "".join(options)
            + "</select>"
            '<button type="submit">View bundle</button>'
            "</form>"
            "<p>Bundles are listed by file modification time, "
            "newest first.</p>"
            '<p><a href="/">View latest bundle</a></p>'
            "</section>"
        )

        selection_note = (
            "Showing the latest bundle by file modification time."
            if bundle is None
            else "Showing the bundle you selected."
        )

        data = json.loads(bundle_path.read_bytes())

        if not isinstance(data, dict) or data.get("target") != "BRCA1":
            raise ValueError("Expected a BRCA1 evidence bundle.")

        verified_count = report.verify_raw_files(data)

        # Import here to avoid a circular import during startup.
        from app.main import (
            GeneResponse,
            LiteratureResponse,
            ProteinResponse,
        )

        gene = GeneResponse.model_validate(data["gene"])
        protein = ProteinResponse.model_validate(data["protein"])
        literature = LiteratureResponse.model_validate(
            data["literature"]
        )

        body = f"""
{selector}

<section>
<h2>Saved evidence bundle</h2>
<p class="meta">{text(bundle_path.name)}</p>
<p>{text(selection_note)}</p>
<p><strong>{verified_count} raw files verified</strong>
against the hashes recorded in this bundle.</p>
<p>Checksum checks establish file integrity, not scientific accuracy.</p>
</section>

<section>
<h2>Gene identity</h2>
<p><strong>{text(gene.gene)}</strong>
— {text(gene.organism)}</p>
<p>NCBI Gene ID: {text(gene.gene_id)}</p>
<p><a href="https://www.ncbi.nlm.nih.gov/gene/672">
Open NCBI Gene record</a></p>
<p class="meta">Retrieved:
{text(gene.retrieved_at_utc.isoformat())}</p>
</section>

<section>
<h2>Protein identity</h2>
<p>UniProt accession: <strong>{text(protein.accession)}</strong></p>
<p>Organism: {text(protein.organism)}</p>
<p><a href="https://www.uniprot.org/uniprotkb/P38398/entry">
Open UniProt record</a></p>
<p class="meta">Retrieved:
{text(protein.retrieved_at_utc.isoformat())}</p>
</section>

<section>
<h2>PubMed literature</h2>
<p>Query: {text(literature.query)}</p>
<p>{len(literature.articles)} articles included;
{text(literature.total_matching_records)} matching records
at retrieval.</p>
<p class="meta">Search retrieved:
{text(literature.search_provenance.retrieved_at_utc.isoformat())}</p>
<p>Search ordering: {text(literature.sort)}.
Search relevance does not measure evidence strength.
These results are not a systematic review.</p>
</section>
"""

        if not literature.articles:
            body += "<section><p>No articles were returned.</p></section>"

        for number, article in enumerate(literature.articles, start=1):
            abstract = article.abstract or "No abstract available."
            body += f"""
<article>
<h3>{number}. {text(article.title)}</h3>
<p><a href="https://pubmed.ncbi.nlm.nih.gov/{text(article.pmid)}/">
PubMed PMID: {text(article.pmid)}</a></p>
<details>
<summary>Read abstract</summary>
<p class="abstract">{text(abstract)}</p>
</details>
</article>
"""

        body += '<p><a href="/docs">Open API documentation</a></p>'
        return page(body)

    except (OSError, ValueError, KeyError, TypeError) as exc:
        return page(
            "<section><h2>Evidence could not be displayed</h2>"
            f"<p>{text(exc)}</p>"
            "<p>Check the saved bundle and its raw files.</p>"
            '<p><a href="/">Return to the latest bundle</a></p>'
            "</section>",
            status_code=500,
        )