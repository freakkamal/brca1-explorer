"""Local browser viewer for saved BRCA1 evidence."""

import json
import hashlib
from html import escape
import secrets

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from urllib.parse import urlencode, parse_qs

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
<p><a href="/">Evidence viewer</a> | <a href="/compare-bundles">Compare bundles</a></p>
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
            '<p><a href="/compounds">Find a compound in PubChem</a></p>'
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
<p><a href="{text('/download-summary-review?' + urlencode({'summary': summary_path.name, 'digest': hashlib.sha256(summary_bytes).hexdigest()}))}">Download summary and review report</a></p>
{review_form(summary_path, summary_bytes, cited_pmids)}
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

        matching.sort(
        key=lambda item: (item[0], item[1]),
        reverse=True,
        )
        latest = matching[0][2]

        history_items = []
        for reviewed_at, filename, record in matching:
            checked_sources = ", ".join(
                sorted(set(record["checked_pmids"]), key=int)
            )
            history_items.append(
                "<article>"
                f"<h4>{text(labels[record['decision']])}</h4>"
                f"<p>Reviewer: {text(record['reviewer'])}</p>"
                f"<p>Recorded time: {text(record['reviewed_at_utc'])}</p>"
                f"<p>Scope: {text(scope_labels[record['scope']])}</p>"
                f"<p>Checked PMIDs: {text(checked_sources)}</p>"
                f"<div class=\"abstract\">{text(record['notes'])}</div>"
                "</article>"
            )

        history_html = (
            "<details>"
            f"<summary>Review history ({len(matching)} records)</summary>"
            "<p>Newest recorded review first. "
            "Only reviews matching this exact summary version are shown.</p>"
            + "".join(history_items)
            + "</details>"
        )

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
{history_html}
</div>
"""

    except (OSError, ValueError, KeyError, TypeError) as exc:
        return (
            "<p><strong>Review status unavailable</strong></p>"
            f"<p>{text(exc)}</p>"
            "<p>Review records could not be validated. "
            "No reviewed status is being asserted.</p>"
        )


# Refresh the browser after restarting the server to get a fresh token.
REVIEW_FORM_TOKEN = secrets.token_hex(32)


def review_form(summary_path, summary_bytes, cited_pmids):
    """Build a form tied to the summary version currently displayed."""
    digest = hashlib.sha256(summary_bytes).hexdigest()
    checkboxes = "".join(
        f'<label style="display:block">'
        f'<input type="checkbox" name="checked_pmids" value="{text(pmid)}">'
        f' PMID {text(pmid)}</label>'
        for pmid in cited_pmids
    )

    return f"""
<details>
<summary>Record a review</summary>
<form action="/save-review" method="post">
<input type="hidden" name="token" value="{REVIEW_FORM_TOKEN}">
<input type="hidden" name="summary" value="{text(summary_path.name)}">
<input type="hidden" name="summary_digest" value="{digest}">

<p>
<label for="reviewer">Reviewer name</label><br>
<input id="reviewer" name="reviewer" required maxlength="200"
style="width:100%;box-sizing:border-box;padding:8px">
</p>

<fieldset>
<legend>Sources you actually checked</legend>
{checkboxes}
</fieldset>

<label for="review-scope">Review scope</label>
<select id="review-scope" name="scope">
<option value="selected_claims">Selected claims only</option>
<option value="whole_summary">Whole summary</option>
</select>

<label for="review-decision">Decision</label>
<select id="review-decision" name="decision">
<option value="in_progress">Review in progress</option>
<option value="changes_requested">Changes requested</option>
<option value="reviewed">Reviewed</option>
</select>

<p>
<label for="review-notes">Review notes</label><br>
<textarea id="review-notes" name="notes" rows="7" required
maxlength="10000"
style="width:100%;box-sizing:border-box;padding:8px"
placeholder="Describe what you checked, the evidence used, and any corrections needed."></textarea>
</p>

<p>Choose Reviewed only after checking the entire summary.
All cited sources must be selected for that decision.
Review completion is self-reported, not clinical validation.</p>

<button type="submit">Save review</button>
</form>
</details>
"""


@router.post("/save-review", response_class=HTMLResponse, tags=["Local viewer"])
async def submit_review(request: Request):
    """Save a browser-submitted review for an exact summary version."""
    from app import reviews

    try:
        content_type = request.headers.get("content-type", "").split(";")[0]
        if content_type != "application/x-www-form-urlencoded":
            return page("<p>Unsupported form format.</p>", status_code=415)

        # Bound the request size before parsing it.
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 100000:
                return page("<p>Review form is too large.</p>", status_code=413)

        fields = parse_qs(
            body.decode("utf-8"),
            keep_blank_values=True,
            max_num_fields=100,
        )

        def single(name):
            values = fields.get(name, [])
            if len(values) != 1:
                raise ValueError(f"Missing or repeated field: {name}")
            return values[0]

        token = single("token")
        if not secrets.compare_digest(
            token.encode("utf-8"),
            REVIEW_FORM_TOKEN.encode("utf-8"),
        ):
            return page(
                "<p>This form has expired or is invalid. "
                "Refresh the viewer and try again.</p>",
                status_code=403,
            )

        filename = single("summary")
        directory = (storage.PROJECT_ROOT / "data/summaries").resolve()
        available = {
            path.name: path
            for path in directory.glob("brca1-*.json")
            if path.is_file() and path.resolve().is_relative_to(directory)
        }

        if filename not in available:
            return page("<p>Summary not found.</p>", status_code=404)

        summary_path = available[filename]
        summary_bytes = summary_path.read_bytes()
        actual_digest = hashlib.sha256(summary_bytes).hexdigest()

        if single("summary_digest") != actual_digest:
            return page(
                "<p>The summary changed after this form was opened. "
                "Refresh the viewer before reviewing it.</p>",
                status_code=409,
            )

        reviewer = single("reviewer")
        notes = single("notes")
        if len(reviewer) > 200 or len(notes) > 10000:
            raise ValueError("Reviewer name or notes exceed the length limit.")

        saved_summary = json.loads(summary_bytes)

        destination = reviews.save_review(
            summary_path=summary_path,
            reviewer=reviewer,
            decision=single("decision"),
            notes=notes,
            checked_pmids=fields.get("checked_pmids", []),
            scope=single("scope"),
        )

        return_url = "/?" + urlencode(
            {"bundle": saved_summary["bundle_filename"]}
        )
        return page(
            "<section><h2>Review saved</h2>"
            f"<p>Record: {text(destination.name)}</p>"
            "<p>The original summary was not changed.</p>"
            f'<p><a href="{text(return_url)}">'
            "Return to the evidence and review status</a></p>"
            "</section>"
        )

    except (ValueError, KeyError, TypeError) as exc:
        return page(
            "<section><h2>Review not saved</h2>"
            f"<p>{text(exc)}</p>"
            "<p>Use your browser's Back button to correct the form.</p>"
            "</section>",
            status_code=400,
        )
    except OSError:
        return page(
            "<section><h2>Review could not be saved</h2>"
            "<p>A file could not be read or written. "
            "Check the project files and folder permissions.</p></section>",
            status_code=500,
        )

@router.get("/download-summary-review", tags=["Local viewer"])
def download_summary_review(summary: str, digest: str):
    """Download an exact summary version with its current review history."""
    from app.summaries import extract_pmids

    try:
        directory = (storage.PROJECT_ROOT / "data/summaries").resolve()
        available = {
            path.name: path
            for path in directory.glob("brca1-*.json")
            if path.is_file() and path.resolve().is_relative_to(directory)
        }

        if summary not in available:
            return page("<p>Summary not found.</p>", status_code=404)

        summary_bytes = available[summary].read_bytes()
        file_digest = hashlib.sha256(summary_bytes).hexdigest()

        if digest != file_digest:
            return page(
                "<p>The summary changed. Refresh the viewer "
                "and download again.</p>",
                status_code=409,
            )

        saved = json.loads(summary_bytes)
        if not isinstance(saved, dict) or saved.get("target") != "BRCA1":
            raise ValueError("Expected a BRCA1 summary.")

        summary_text = saved["summary_markdown"]
        if not isinstance(summary_text, str) or not summary_text.strip():
            raise ValueError("Summary text is missing.")

        text_digest = hashlib.sha256(
            summary_text.encode("utf-8")
        ).hexdigest()
        if text_digest != saved["summary_sha256"]:
            raise ValueError("Summary text checksum mismatch.")

        bundle_root = (storage.PROJECT_ROOT / "data/bundles").resolve()
        bundle_path = (bundle_root / saved["bundle_filename"]).resolve()

        if not bundle_path.is_relative_to(bundle_root):
            raise ValueError("Bundle path is outside data/bundles.")

        bundle_bytes = bundle_path.read_bytes()
        bundle_digest = hashlib.sha256(bundle_bytes).hexdigest()
        if bundle_digest != saved["bundle_sha256"]:
            raise ValueError("Bundle checksum mismatch.")

        bundle = json.loads(bundle_bytes)
        if not isinstance(bundle, dict) or bundle.get("target") != "BRCA1":
            raise ValueError("Expected a BRCA1 evidence bundle.")

        verified_count = report.verify_raw_files(bundle)

        cited_pmids = extract_pmids(summary_text)
        allowed_pmids = {
            str(article["pmid"])
            for article in bundle["literature"]["articles"]
        }
        if not cited_pmids or not set(cited_pmids).issubset(allowed_pmids):
            raise ValueError("Summary citations do not match the bundle.")

        links = " | ".join(
            f'<a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/">'
            f"PMID {pmid}</a>"
            for pmid in cited_pmids
        )

        # Reuse the viewer's validation and ordering of review records.
        review_html = review_section(summary_bytes, saved, cited_pmids)

        body = f"""
<section>
<h2>AI summary and review report</h2>
<p>This download captures the review records available at download time.
It does not update when later reviews are added.</p>
<p>Origin: {text(saved["origin"])}</p>
<p>Imported: {text(saved["imported_at_utc"])}</p>
<p class="meta">Bundle file: {text(saved["bundle_filename"])}</p>
<p class="meta">Bundle SHA-256: {bundle_digest}</p>
<p class="meta">Summary file SHA-256: {file_digest}</p>
<p class="meta">Summary text SHA-256: {text_digest}</p>
<p>Raw files verified: {verified_count}</p>
<p>Checksums establish integrity, not scientific accuracy.
Citation membership does not establish that sources support every claim.</p>
</section>

<section>
<h2>Recorded review status and history</h2>
<p>Reviewer identity and review completion are self-reported.
Reviewed does not mean clinically validated.</p>
{review_html}
</section>

<section>
<h2>Imported AI summary — original text</h2>
<p>Status wording inside the original text reflects the imported draft.
The recorded review status is shown above.</p>
<div class="abstract">{text(summary_text)}</div>
<p><strong>Cited articles:</strong> {links}</p>
</section>
"""
        response = page(body)
        response.headers["Content-Disposition"] = (
            'attachment; filename="brca1-summary-review-'
            + file_digest
            + '.html"'
        )
        return response

    except (OSError, ValueError, KeyError, TypeError) as exc:
        return page(
            "<section><h2>Summary report could not be created</h2>"
            f"<p>{text(exc)}</p>"
            "<p>Check the summary, evidence bundle, and raw files.</p>"
            "</section>",
            status_code=500,
        )

@router.get("/compare-bundles", response_class=HTMLResponse, tags=["Local viewer"])
def compare_bundles_page(
    baseline: str | None = None,
    comparison: str | None = None,
):
    """Choose and compare two saved evidence bundles."""
    from app import compare

    try:
        directory = (storage.PROJECT_ROOT / "data/bundles").resolve()
        candidates = [
            path
            for path in directory.glob("brca1-*.json")
            if path.is_file() and path.resolve().is_relative_to(directory)
        ]
        candidates.sort(
            key=lambda path: (path.stat().st_mtime_ns, path.name),
            reverse=True,
        )
        available = {path.name for path in candidates}

        for selected in (baseline, comparison):
            if selected is not None and selected not in available:
                return page(
                    "<p>The requested bundle is not available.</p>"
                    '<p><a href="/compare-bundles">Choose bundles</a></p>',
                    status_code=404,
                )

        if not candidates:
            return page(
                "<section><h2>No saved bundles available</h2>"
                "<p>Create evidence bundles before comparing them.</p>"
                '<p><a href="/">Return to the viewer</a></p></section>'
            )

        def options(selected):
            items = ['<option value="">Choose a bundle</option>']
            for path in candidates:
                chosen = " selected" if path.name == selected else ""
                items.append(
                    f'<option value="{text(path.name)}"{chosen}>'
                    f"{text(path.name)}</option>"
                )
            return "".join(items)

        body = f"""
<section>
<h2>Compare evidence bundles</h2>
<p>Select a baseline and a comparison bundle.
Their roles are determined by your selections, not by their dates.</p>
<form action="/compare-bundles" method="get">
<label for="baseline">Baseline bundle</label>
<select id="baseline" name="baseline" required>
{options(baseline)}
</select>
<label for="comparison">Comparison bundle</label>
<select id="comparison" name="comparison" required>
{options(comparison)}
</select>
<button type="submit">Compare bundles</button>
</form>
<p><a href="/">Return to the evidence viewer</a></p>
</section>
"""

        if baseline is None or comparison is None:
            return page(body)

        result = compare.compare_bundles(baseline, comparison)
        counts = result["counts"]

        body += "<section><h2>Comparison results</h2>"
        for key, label in (
            ("baseline", "Baseline"),
            ("comparison", "Comparison"),
        ):
            metadata = result[key]
            body += (
                f"<h3>{label}</h3>"
                f'<p class="meta">{text(metadata["filename"])}</p>'
                f'<p class="meta">SHA-256: {text(metadata["sha256"])}</p>'
                f'<p>Raw files verified: {metadata["raw_files_verified"]}</p>'
                f'<p>Query: {text(metadata["query"])}</p>'
                f'<p>Ordering: {text(metadata["sort"])}</p>'
            )

        body += "<dl>"
        for key, label in (
            ("baseline_articles", "Articles in baseline"),
            ("comparison_articles", "Articles in comparison"),
            ("only_in_comparison", "Only in comparison"),
            ("only_in_baseline", "Only in baseline"),
            ("shared", "Shared articles"),
            ("shared_with_text_changes", "Shared articles with text changes"),
        ):
            body += f"<dt>{label}</dt><dd>{counts[key]}</dd>"
        body += "</dl></section>"

        body += "<section><h2>How to interpret these results</h2><ul>"
        for limitation in result["limitations"]:
            body += f"<li>{text(limitation)}</li>"
        body += "</ul></section>"

        for key, heading in (
            ("only_in_comparison", "Articles only in comparison"),
            ("only_in_baseline", "Articles only in baseline"),
        ):
            body += f"<section><h2>{heading}</h2>"
            if not result[key]:
                body += "<p>None.</p>"
            for article in result[key]:
                body += (
                    f'<h3>{text(article["title"])}</h3>'
                    f'<p><a href="{text(article["record_url"])}">'
                    f'PMID {text(article["pmid"])}</a></p>'
                    "<details><summary>Read saved abstract</summary>"
                    '<div class="abstract">'
                    + text(article["abstract"] or "No abstract available.")
                    + "</div></details>"
                )
            body += "</section>"

        body += "<section><h2>Shared articles</h2>"
        if not result["shared_pmids"]:
            body += "<p>None.</p>"
        else:
            body += "<ul>"
            for pmid in result["shared_pmids"]:
                body += (
                    f'<li><a href="https://pubmed.ncbi.nlm.nih.gov/{text(pmid)}/">'
                    f"PMID {text(pmid)}</a></li>"
                )
            body += "</ul>"

        body += "<h3>Changes to saved titles or abstracts</h3>"
        if not result["shared_text_changes"]:
            body += "<p>No text changes among shared articles.</p>"
        else:
            body += "<ul>"
            for change in result["shared_text_changes"]:
                fields = ", ".join(change["changed_fields"])
                body += (
                    f'<li>PMID {text(change["pmid"])}: '
                    f"{text(fields)}</li>"
                )
            body += "</ul>"
        body += "</section>"

        return page(body)

    except (OSError, ValueError, KeyError, TypeError) as exc:
        return page(
            "<section><h2>Comparison could not be completed</h2>"
            f"<p>{text(exc)}</p>"
            '<p><a href="/compare-bundles">Choose bundles again</a></p>'
            "</section>",
            status_code=500,
        )
@router.get("/compounds", response_class=HTMLResponse, tags=["Compound lookup"])
def compound_lookup_page(name: str | None = None):
    """Search PubChem by name and display all matching compound IDs."""
    from app import pubchem

    query = (name or "").strip()
    form = f"""
<section>
<h2>Find a compound</h2>
<p><a href="/literature-mentions">Find mentions in saved BRCA1 literature</a></p>
<p><a href="/compare-compounds">Compare two compounds by CID</a></p>
<form action="/compounds" method="get">
<label for="compound-name">Compound name</label>
<input id="compound-name" name="name" value="{text(query)}"
       placeholder="Example: aspirin" required maxlength="200">
<button type="submit">Search PubChem</button>
</form>
<p>A name match identifies a chemical record. It does not establish
activity against BRCA1.</p>
<p><a href="/">Return to the evidence viewer</a></p>
</section>
"""

    if name is None:
        return page(form)

    if not query or len(query) > 200:
        return page(
            form + "<p>Enter a compound name between 1 and 200 characters.</p>",
            status_code=400,
        )

    try:
        result = pubchem.lookup_compound(query)
    except ValueError as exc:
        return page(form + f"<p>{text(exc)}</p>", status_code=404)
    except RuntimeError as exc:
        return page(form + f"<p>{text(exc)}</p>", status_code=502)
    except OSError:
        return page(form + "<p>Could not save the PubChem response.</p>",
                    status_code=500)

    items = "".join(
        f'<li><a href="{text(match["record_url"])}">'
        f'PubChem CID {text(match["cid"])}</a> | '
        f'<a href="/compounds/{text(match["cid"])}">View compound details</a></li>'
        for match in result["matches"]
    )

    return page(form + f"""
<section>
<h2>Results for {text(query)}</h2>
<p>Matching compound IDs: {len(result["matches"])}</p>
<ul>{items}</ul>
<p>Retrieved (UTC): {text(result["retrieved_at_utc"])}</p>
<p class="meta">Saved response: {text(result["raw_file"])}</p>
<p class="meta">Response SHA-256: {text(result["response_sha256"])}</p>
</section>
""")

@router.get("/compounds/{cid}", response_class=HTMLResponse, tags=["Compound lookup"])
def compound_details_page(cid: str):
    from app.compound_details import CompoundNotFound, fetch_compound_details

    back = '<p><a href="/compounds">Return to compound search</a></p>'

    try:
        data = fetch_compound_details(cid)
    except CompoundNotFound as exc:
        return page(f"<p>{text(exc)}</p>" + back, status_code=404)
    except ValueError as exc:
        return page(f"<p>{text(exc)}</p>" + back, status_code=400)
    except RuntimeError as exc:
        return page(f"<p>{text(exc)}</p>" + back, status_code=502)
    except OSError:
        return page("<p>Could not save the PubChem response.</p>" + back,
                    status_code=500)

    return page(f"""
<section>
<h2>Compound details: PubChem CID {text(data["cid"])}</h2>
<dl>
<dt>Molecular formula</dt><dd>{text(data["molecular_formula"])}</dd>
<dt>Molecular weight</dt><dd>{text(data["molecular_weight_g_mol"])} g/mol</dd>
</dl>
<p><a href="{text(data["record_url"])}">Open the PubChem compound record</a></p>
<p class="meta">Retrieved (UTC): {text(data["retrieved_at_utc"])}</p>
<p class="meta">Saved response: {text(data["raw_file"])}</p>
<p class="meta">Response SHA-256: {text(data["response_sha256"])}</p>
{back}
</section>
""")

@router.get("/compare-compounds", response_class=HTMLResponse, tags=["Compound lookup"])
def compare_compounds_page(left: str | None = None, right: str | None = None):
    """Compare the PubChem properties of two user-selected CIDs."""
    import re
    from app.compound_details import CompoundNotFound, fetch_compound_details

    first = (left or "").strip()
    second = (right or "").strip()

    form = f"""
<section>
<h2>Compare two compounds</h2>
<form action="/compare-compounds" method="get">
<p><label>First PubChem CID
<input name="left" value="{text(first)}" placeholder="2244"
       inputmode="numeric" pattern="[1-9][0-9]*" required></label></p>
<p><label>Second PubChem CID
<input name="right" value="{text(second)}" placeholder="241"
       inputmode="numeric" pattern="[1-9][0-9]*" required></label></p>
<button type="submit">Compare compounds</button>
</form>
<p><a href="/compounds">Find a CID by compound name</a></p>
</section>
"""

    if left is None and right is None:
        return page(form)

    # Validate both inputs before contacting PubChem.
    if not all(re.fullmatch(r"[1-9][0-9]*", cid) for cid in (first, second)):
        return page(form + "<p>Enter two positive whole-number CIDs.</p>",
                    status_code=400)
    if first == second:
        return page(form + "<p>Choose two different CIDs.</p>", status_code=400)

    records = []
    for cid in (first, second):
        try:
            records.append(fetch_compound_details(cid))
        except CompoundNotFound as exc:
            return page(form + f"<p>{text(exc)}</p>", status_code=404)
        except RuntimeError as exc:
            return page(form + f"<p>Lookup failed for CID {text(cid)}: "
                        f"{text(exc)}</p>", status_code=502)
        except OSError:
            return page(form + "<p>Could not save the PubChem response.</p>",
                        status_code=500)

    a, b = records

    def source_link(record):
        return (
            f'<a href="{text(record["record_url"])}">'
            f'PubChem CID {text(record["cid"])}</a>'
        )

    return page(form + f"""
<section>
<h2>Comparison results</h2>
<table cellpadding="8">
<caption>Properties reported by PubChem</caption>
<thead>
<tr><th scope="col">Property</th>
<th scope="col">{source_link(a)}</th><th scope="col">{source_link(b)}</th></tr>
</thead>
<tbody>
<tr><th scope="row">Molecular formula</th>
<td>{text(a["molecular_formula"])}</td><td>{text(b["molecular_formula"])}</td></tr>
<tr><th scope="row">Molecular weight (g/mol)</th>
<td>{text(a["molecular_weight_g_mol"])}</td><td>{text(b["molecular_weight_g_mol"])}</td></tr>
</tbody>
</table>
<p>These properties alone do not establish activity against BRCA1.</p>
</section>
""")

@router.get("/literature-mentions", response_class=HTMLResponse, tags=["Local viewer"])
def literature_mentions_page(bundle: str | None = None, q: str = ""):
    from app.mentions import find_mentions

    root = (storage.PROJECT_ROOT / "data/bundles").resolve()
    back = '<p><a href="/">Return to the evidence viewer</a></p>'

    try:
        names = sorted(
            path.name for path in root.glob("brca1-*.json")
            if path.is_file() and path.resolve().is_relative_to(root)
        )
        if bundle is not None and bundle not in names:
            return page("<p>Selected bundle not found.</p>" + back, status_code=404)
        if not names:
            return page("<p>No saved evidence bundles are available.</p>" + back)

        options = "".join(
            f'<option value="{text(name)}"'
            + (" selected" if name == bundle else "")
            + f">{text(name)}</option>"
            for name in names
        )
        body = f"""
<section>
<h2>Find mentions in saved literature</h2>
<form action="/literature-mentions" method="get">
<label for="bundle">Evidence bundle</label>
<select id="bundle" name="bundle" required>{options}</select>
<label for="q">Compound name or phrase</label>
<input id="q" name="q" value="{text(q)}" maxlength="120"
       placeholder="Example: olaparib" required>
<button type="submit">Find mentions</button>
</form>
<p>Searches the saved titles and abstracts for the text you enter.
Synonyms and abbreviations are not expanded.</p>
</section>
"""
        if bundle is None:
            return page(body + back)
        if not q.strip() or len(q.strip()) > 120:
            return page(body + "<p>Enter 1 to 120 characters.</p>" + back,
                        status_code=400)

        result = find_mentions(bundle, q)
        matches = result["matches"]
        body += (
            "<section><h2>Text mentions</h2>"
            f"<p>{len(matches)} of {result['article_count']} saved articles "
            f"matched <strong>{text(q.strip())}</strong>.</p>"
            f'<p class="meta">Bundle SHA-256: {text(result["sha256"])}</p>'
            "<p>A text mention alone does not establish binding, activity "
            "against BRCA1, or treatment benefit.</p></section>"
        )

        for item in matches:
            pmid = text(item["pmid"])
            body += (
                f"<article><h3>{text(item['title'])}</h3>"
                f'<p><a href="https://pubmed.ncbi.nlm.nih.gov/{pmid}/">'
                f"PubMed PMID: {pmid}</a></p>"
            )
            if item["title_match"]:
                body += "<p><strong>Match in title</strong></p>"
            for passage in item["passages"]:
                body += f"<blockquote>{text(passage)}</blockquote>"
            body += "</article>"

        return page(body + back)

    except (OSError, ValueError, KeyError, TypeError) as exc:
        return page("<p>Could not search the saved evidence: "
                    + text(exc) + "</p>" + back, status_code=500)