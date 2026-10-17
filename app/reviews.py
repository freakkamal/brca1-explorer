"""Record human reviews without modifying imported AI summaries."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from uuid import uuid4

from app import report, storage
from app.summaries import extract_pmids, project_path


DECISIONS = ("in_progress", "changes_requested", "reviewed")


def save_review(
    summary_path,
    reviewer,
    decision,
    notes,
    checked_pmids,
    scope="selected_claims",
):
    """Save a review linked to the exact summary file and evidence."""
    reviewer = reviewer.strip()
    notes = notes.strip()

    if not reviewer:
        raise ValueError("Reviewer name is required.")
    if not notes:
        raise ValueError("Review notes are required.")
    if decision not in DECISIONS:
        raise ValueError("Unknown review decision.")
    if scope not in ("selected_claims", "whole_summary"):
        raise ValueError("Unknown review scope.")

    summary_path = project_path(summary_path)
    summary_root = (storage.PROJECT_ROOT / "data/summaries").resolve()

    if not summary_path.is_relative_to(summary_root):
        raise ValueError("Choose a summary inside data/summaries.")

    summary_bytes = summary_path.read_bytes()
    summary = json.loads(summary_bytes)

    if not isinstance(summary, dict) or summary.get("target") != "BRCA1":
        raise ValueError("Expected a BRCA1 summary.")

    summary_text = summary["summary_markdown"]
    if not isinstance(summary_text, str) or not summary_text.strip():
        raise ValueError("Summary text is missing.")

    text_digest = hashlib.sha256(
        summary_text.encode("utf-8")
    ).hexdigest()
    if text_digest != summary["summary_sha256"]:
        raise ValueError("Summary text checksum mismatch.")

    bundle_root = (storage.PROJECT_ROOT / "data/bundles").resolve()
    bundle_path = (bundle_root / summary["bundle_filename"]).resolve()

    if not bundle_path.is_relative_to(bundle_root):
        raise ValueError("Bundle path is outside data/bundles.")

    bundle_bytes = bundle_path.read_bytes()
    bundle_digest = hashlib.sha256(bundle_bytes).hexdigest()

    if bundle_digest != summary["bundle_sha256"]:
        raise ValueError("Bundle checksum mismatch.")

    bundle = json.loads(bundle_bytes)
    if not isinstance(bundle, dict) or bundle.get("target") != "BRCA1":
        raise ValueError("Expected a BRCA1 evidence bundle.")

    report.verify_raw_files(bundle)

    cited_pmids = set(extract_pmids(summary_text))
    allowed_pmids = {
        str(article["pmid"])
        for article in bundle["literature"]["articles"]
    }

    if not cited_pmids or not cited_pmids.issubset(allowed_pmids):
        raise ValueError("Summary citations do not match the bundle.")

    checked = {str(pmid).strip() for pmid in checked_pmids}

    if not checked or not checked.issubset(cited_pmids):
        raise ValueError(
            "Specify checked PMIDs that are cited in this summary."
        )

    if decision == "reviewed":
        if scope != "whole_summary" or checked != cited_pmids:
            raise ValueError(
                "Reviewed requires whole_summary scope and all cited PMIDs. "
                "Use in_progress for a partial review."
            )

    review_id = uuid4().hex
    record = {
        "schema_version": "1.0",
        "review_id": review_id,
        "summary_id": summary["summary_id"],
        "summary_filename": summary_path.name,
        "summary_file_sha256": hashlib.sha256(
            summary_bytes
        ).hexdigest(),
        "summary_sha256": text_digest,
        "bundle_sha256": bundle_digest,
        "reviewer": reviewer,
        "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "scope": scope,
        "checked_pmids": sorted(checked, key=int),
        "notes": notes,
        "limitations": (
            "Reviewer identity and review completion are self-reported. "
            "Software checks file integrity and citation membership, "
            "not the scientific quality of the review. "
            "Reviewed does not mean clinically validated."
        ),
    }

    directory = storage.PROJECT_ROOT / "data/reviews"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"review-{review_id}.json"

    with destination.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return destination


def main():
    parser = argparse.ArgumentParser(
        description="Record a human review of an imported BRCA1 summary."
    )
    parser.add_argument("summary", help="Exact imported summary JSON path.")
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--decision", required=True, choices=DECISIONS)
    parser.add_argument("--notes-file", required=True)
    parser.add_argument("--checked-pmids", required=True, nargs="+")
    parser.add_argument(
        "--scope",
        choices=("selected_claims", "whole_summary"),
        default="selected_claims",
    )
    args = parser.parse_args()

    try:
        notes = project_path(args.notes_file).read_text(
            encoding="utf-8-sig"
        )
        destination = save_review(
            summary_path=args.summary,
            reviewer=args.reviewer,
            decision=args.decision,
            notes=notes,
            checked_pmids=args.checked_pmids,
            scope=args.scope,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Review could not be saved: {exc}\n")

    print(f"Review saved: {destination}")
    print(f"Decision: {args.decision}")
    print("Original summary unchanged.")


if __name__ == "__main__":
    main()