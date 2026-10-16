"""Import manually generated AI summaries linked to evidence bundles."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

from app import report, storage


def project_path(value):
    """Resolve a relative path against the project directory."""
    path = Path(value)
    if not path.is_absolute():
        path = storage.PROJECT_ROOT / path
    return path.resolve()


def extract_pmids(summary_text):
    """Read citations written as PMID labels or standard PubMed URLs."""
    labelled = re.findall(
        r"\bPMID\s*:?\s*([1-9][0-9]*)\b",
        summary_text,
        flags=re.IGNORECASE,
    )
    linked = re.findall(
        r"https?://pubmed\.ncbi\.nlm\.nih\.gov/([1-9][0-9]*)(?=[/?#\s)]|$)",
        summary_text,
        flags=re.IGNORECASE,
    )
    return sorted(set(labelled + linked), key=int)


def import_summary(bundle_path, summary_path, expected_bundle_sha256):
    """Validate and save a summary without changing source evidence."""
    if not re.fullmatch(r"[0-9a-f]{64}", expected_bundle_sha256):
        raise ValueError("Expected bundle checksum must be 64 hex characters.")

    bundle_path = project_path(bundle_path)
    bundle_root = (storage.PROJECT_ROOT / "data/bundles").resolve()

    if not bundle_path.is_relative_to(bundle_root):
        raise ValueError("Choose a bundle inside data/bundles.")

    bundle_bytes = bundle_path.read_bytes()
    bundle_digest = hashlib.sha256(bundle_bytes).hexdigest()

    if bundle_digest != expected_bundle_sha256:
        raise ValueError(
            "Bundle checksum does not match the report used for the summary."
        )

    bundle = json.loads(bundle_bytes)
    if not isinstance(bundle, dict) or bundle.get("target") != "BRCA1":
        raise ValueError("Expected a BRCA1 evidence bundle.")

    report.verify_raw_files(bundle)

    summary_text = project_path(summary_path).read_text(
        encoding="utf-8-sig"
    ).strip()

    if not summary_text:
        raise ValueError("The summary file is empty.")

    articles = bundle["literature"]["articles"]
    allowed_pmids = {str(article["pmid"]) for article in articles}
    cited_pmids = extract_pmids(summary_text)

    if not cited_pmids:
        raise ValueError(
            "No citations found. Use PMID: 123456 or a standard PubMed URL."
        )

    unknown_pmids = set(cited_pmids) - allowed_pmids
    if unknown_pmids:
        raise ValueError(
            "These cited PMIDs are absent from the bundle: "
            + ", ".join(sorted(unknown_pmids, key=int))
        )

    summary_id = uuid4().hex
    record = {
        "schema_version": "1.0",
        "summary_id": summary_id,
        "target": "BRCA1",
        "evidence_type": "ai_generated_summary",
        "origin": "ChatGPT — manually imported",
        "review_status": "not_yet_reviewed",
        "imported_at_utc": datetime.now(timezone.utc).isoformat(),
        "bundle_id": bundle["bundle_id"],
        "bundle_filename": bundle_path.name,
        "bundle_sha256": bundle_digest,
        "summary_sha256": hashlib.sha256(
            summary_text.encode("utf-8")
        ).hexdigest(),
        "cited_pmids": cited_pmids,
        "citation_check": "recognized_pmids_belong_to_bundle",
        "limitations": (
            "Checks PMID labels and standard PubMed URLs only. "
            "Does not verify that citations support claims, that all claims "
            "are cited, or that the summary faithfully represents the papers."
        ),
        "summary_markdown": summary_text,
    }

    directory = storage.PROJECT_ROOT / "data/summaries"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"brca1-{bundle_digest}-{summary_id}.json"

    # Exclusive creation prevents overwriting an existing summary.
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return destination


def main():
    parser = argparse.ArgumentParser(
        description="Import a ChatGPT summary for a verified BRCA1 bundle."
    )
    parser.add_argument("bundle", help="Original bundle JSON file.")
    parser.add_argument("summary", help="Text or Markdown summary file.")
    parser.add_argument(
        "--expected-bundle-sha256",
        required=True,
        help="Bundle SHA-256 shown in the evidence report.",
    )
    args = parser.parse_args()

    try:
        destination = import_summary(
            args.bundle,
            args.summary,
            args.expected_bundle_sha256,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Summary import failed: {exc}\n")

    print(f"Summary saved: {destination}")
    print("Review status: Not yet reviewed")
    print("Recognized PMID citations belong to the selected bundle.")
    print("Scientific claims still require review.")


if __name__ == "__main__":
    main()