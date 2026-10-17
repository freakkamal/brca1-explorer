"""Local browser viewer for saved BRCA1 evidence."""

import json
import hashlib
from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, FileResponse
from urllib.parse import urlencode

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
This page displays saved evidence and separately labelled imported AI summaries.
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
        download_url = "/download-report?" + urlencode(
            {"bundle": bundle_path.name}
        )
        
        
        body = f"""
{selector}

<section>
<h2>Saved evidence bundle</h2>
<p class="meta">{text(bundle_path.name)}</p>
<p>{text(selection_note)}</p>
<p><a href="{text(download_url)}">Download Markdown report</a></p>
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
        body += summary_section(bundle_path)
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



@router.get("/download-report", tags=["Local viewer"])
def download_report(bundle: str):
    """Generate and download a report for an available saved bundle."""
    try:
        bundle_directory = storage.PROJECT_ROOT / "data" / "bundles"
        available = {
            path.name: path
            for path in bundle_directory.glob("brca1-*.json")
            if path.is_file()
        }

        if bundle not in available:
            return page(
                "<section><h2>Bundle not found</h2>"
                "<p>The requested bundle is not available.</p>"
                '<p><a href="/">Return to the viewer</a></p>'
                "</section>",
                status_code=404,
            )

        report_path = report.create_report(available[bundle])

        return FileResponse(
            path=report_path,
            media_type="text/markdown",
            filename=report_path.name,
            headers={"Cache-Control": "no-store"},
        )

    except (OSError, ValueError, KeyError, TypeError) as exc:
        return page(
            "<section><h2>Report could not be created</h2>"
            f"<p>{text(exc)}</p>"
            '<p><a href="/">Return to the viewer</a></p>'
            "</section>",
            status_code=500,
        )


def summary_section(bundle_path):
    """Display the latest imported summary for this exact bundle."""
    bundle_digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
    directory = storage.PROJECT_ROOT / "data/summaries"
    candidates = list(
        directory.glob(f"brca1-{bundle_digest}-*.json")
    )

    if not candidates:
        return (
            "<section><h2>AI summary</h2>"
            "<p>No imported summary is saved for this bundle.</p>"
            "</section>"
        )

    try:
        summary_path = max(
            candidates,
            key=lambda path: (path.stat().st_mtime_ns, path.name),
        )
        summary_bytes = summary_path.read_bytes()
        saved = json.loads(summary_bytes)

        if not isinstance(saved, dict):
            raise ValueError("Invalid summary record.")

        if saved["bundle_sha256"] != bundle_digest:
            raise ValueError("Summary belongs to a different bundle.")

        summary_text = saved["summary_markdown"]
        if not isinstance(summary_text, str) or not summary_text.strip():
            raise ValueError("Summary text is missing.")

        actual_digest = hashlib.sha256(
            summary_text.encode("utf-8")
        ).hexdigest()
        if actual_digest != saved["summary_sha256"]:
            raise ValueError("Summary text checksum mismatch.")

        # Recheck recognized citations before displaying source links.
        from app.summaries import extract_pmids

        bundle_data = json.loads(bundle_path.read_bytes())
        allowed_pmids = {
            str(article["pmid"])
            for article in bundle_data["literature"]["articles"]
        }
        cited_pmids = extract_pmids(summary_text)

        if not cited_pmids or not set(cited_pmids).issubset(allowed_pmids):
            raise ValueError("Summary citations do not match this bundle.")

        links = " · ".join(
            f'<a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/">'
            f"PMID {pmid}</a>"
            for pmid in cited_pmids
        )

        return f"""
<section>
<h2>Imported AI summary</h2>
{review_section(summary_bytes, saved, cited_pmids)}
<p>Origin: {text(saved["origin"])}</p>
<p class="meta">Imported: {text(saved["imported_at_utc"])}</p>
<p>Showing the most recently modified summary for this exact bundle.</p>
<p>This is AI-generated interpretation, separate from retrieved evidence.
Citation membership checks do not establish scientific accuracy.</p>
<details>
<summary>Read imported summary</summary>
<div class="abstract">{text(summary_text)}</div>
</details>
<p><strong>Cited articles:</strong> {links}</p>
</section>
"""

    except (OSError, ValueError, KeyError, TypeError) as exc:
        return (
            "<section><h2>AI summary unavailable</h2>"
            f"<p>{text(exc)}</p>"
            "<p>The imported summary could not be validated.</p>"
            "</section>"
        )


def review_section(summary_bytes, summary, cited_pmids):
    """Show the latest recorded review for this exact summary version."""
    from datetime import datetime

    labels = {
        "in_progress": "Review in progress",
        "changes_requested": "Changes requested",
        "reviewed": "Reviewed",
    }
    scope_labels = {
        "selected_claims": "Selected claims only",
        "whole_summary": "Whole summary",
    }

    file_digest = hashlib.sha256(summary_bytes).hexdigest()
    directory = storage.PROJECT_ROOT / "data/reviews"
    matching = []

    try:
        for path in directory.glob("review-*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))

            if not isinstance(record, dict):
                raise ValueError("Invalid review record.")

            # Reviews of other versions must not affect this summary.
            if record.get("summary_file_sha256") != file_digest:
                continue

            if (
                record["summary_id"] != summary["summary_id"]
                or record["summary_sha256"] != summary["summary_sha256"]
                or record["bundle_sha256"] != summary["bundle_sha256"]
            ):
                raise ValueError("Review identifiers do not match the summary.")

            decision = record["decision"]
            scope = record["scope"]

            if decision not in labels or scope not in scope_labels:
                raise ValueError("Invalid review decision or scope.")

            for field in ("reviewer", "notes", "reviewed_at_utc"):
                if (
                    not isinstance(record[field], str)
                    or not record[field].strip()
                ):
                    raise ValueError(f"Review field is missing: {field}")

            checked = record["checked_pmids"]
            if (
                not isinstance(checked, list)
                or not checked
                or not all(isinstance(pmid, str) for pmid in checked)
            ):
                raise ValueError("Invalid checked PMID list.")

            if not set(checked).issubset(set(cited_pmids)):
                raise ValueError("Review references uncited PMIDs.")

            if decision == "reviewed" and (
                scope != "whole_summary"
                or set(checked) != set(cited_pmids)
            ):
                raise ValueError(
                    "A partial review cannot mark the whole summary reviewed."
                )

            reviewed_at = datetime.fromisoformat(record["reviewed_at_utc"])
            if reviewed_at.tzinfo is None:
                raise ValueError("Review timestamp must include a timezone.")

            matching.append((reviewed_at, path.name, record))

        if not matching:
            return (
                "<p><strong>Not yet reviewed</strong></p>"
                "<p>No review record matches this exact summary version.</p>"
            )

        latest = max(matching, key=lambda item: (item[0], item[1]))[2]

        checked_links = " | ".join(
            f'<a href="https://pubmed.ncbi.nlm.nih.gov/{text(pmid)}/">'
            f"PMID {text(pmid)}</a>"
            for pmid in sorted(set(latest["checked_pmids"]), key=int)
        )

        return f"""
<div class="notice">
<p><strong>{labels[latest["decision"]]}</strong></p>
<p>Reviewer: {text(latest["reviewer"])}</p>
<p>Recorded review time: {text(latest["reviewed_at_utc"])}</p>
<p>Scope: {scope_labels[latest["scope"]]}</p>
<p>Checked sources: {checked_links}</p>
<p><strong>Review notes</strong></p>
<div class="abstract">{text(latest["notes"])}</div>
<p>Showing the latest recorded review for this summary version.
A later partial review does not automatically inherit earlier coverage.</p>
<p>Reviewer identity and completion are self-reported.
Reviewed does not mean clinically validated.</p>
</div>
"""

    except (OSError, ValueError, KeyError, TypeError) as exc:
        return (
            "<p><strong>Review status unavailable</strong></p>"
            f"<p>{text(exc)}</p>"
            "<p>Review records could not be validated. "
            "No reviewed status is being asserted.</p>"
        )