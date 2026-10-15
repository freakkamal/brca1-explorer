"""Create a Markdown report from a saved BRCA1 evidence bundle."""

import argparse
import hashlib
import json
from pathlib import Path

from app.storage import PROJECT_ROOT


def verify_raw_files(bundle):
    """Check that referenced raw files exist and match their hashes."""
    raw_files = bundle.get("raw_files")
    if not isinstance(raw_files, list) or not raw_files:
        raise ValueError("The bundle has no raw-file records.")

    raw_root = (PROJECT_ROOT / "data" / "raw").resolve()

    for record in raw_files:
        path = (PROJECT_ROOT / record["path"]).resolve()

        if not path.is_relative_to(raw_root):
            raise ValueError("Raw-file path is outside data/raw.")

        if not path.is_file():
            raise ValueError(f"Raw file is missing: {record['path']}")

        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != record["sha256"]:
            raise ValueError(
                f"Checksum mismatch: {record['path']}"
            )

    return len(raw_files)


def create_report(bundle_path):
    """Verify evidence and write a readable Markdown report."""
    bundle_path = Path(bundle_path)
    if not bundle_path.is_absolute():
        bundle_path = PROJECT_ROOT / bundle_path

    bundle_bytes = bundle_path.read_bytes()
    bundle = json.loads(bundle_bytes)
    bundle_sha256 = hashlib.sha256(bundle_bytes).hexdigest()

    if bundle.get("target") != "BRCA1":
        raise ValueError("Expected a BRCA1 evidence bundle.")

    verified_count = verify_raw_files(bundle)

    protein = bundle["protein"]
    gene = bundle["gene"]
    literature = bundle["literature"]
    articles = literature["articles"]
    provenance = bundle["code_provenance"]

    lines = [
        "# BRCA1 evidence report",
        "",
        "Research use only. Not for clinical decisions.",
        "",
        "This report presents retrieved evidence. "
        "It is not an AI-generated summary or a quality assessment.",
        "",
        "## Bundle details",
        "",
        f"- Bundle ID: {bundle['bundle_id']}",
        f"- Bundle SHA-256: `{bundle_sha256}`",
        f"- Code commit: `{provenance['commit']}`",
        f"- Working tree dirty: {provenance['working_tree_dirty']}",
        f"- Raw files verified: {verified_count}",
        "",
        "The bundle checksum above identifies the file read for this "
        "report. Raw-file checks compare against hashes in that bundle.",
        "",
        "## Gene identity",
        "",
        f"- Gene: {gene['gene']}",
        f"- NCBI Gene ID: {gene['gene_id']}",
        f"- Organism: {gene['organism']}",
        f"- Retrieved at (UTC): {gene['retrieved_at_utc']}",
        f"- Source: {gene['record_url']}",
        "",
        "## Protein identity",
        "",
        f"- UniProt accession: {protein['accession']}",
        f"- Organism: {protein['organism']}",
        f"- Retrieved at (UTC): {protein['retrieved_at_utc']}",
        f"- Source: {protein['record_url']}",
        "",
        "## Literature",
        "",
        f"- Search query: {literature['query']}",
        f"- Search ordering: {literature['sort']}",
        f"- Matching records: {literature['total_matching_records']}",
        f"- Articles included: {len(articles)}",
        "- Search retrieved at (UTC): "
        f"{literature['search_provenance']['retrieved_at_utc']}",
        "",
        "These search results are not a systematic review. "
        "Search ordering does not measure evidence strength.",
        "",
    ]

    if not articles:
        lines.extend(["No articles were returned.", ""])

    for number, article in enumerate(articles, start=1):
        lines.extend([
            f"### {number}. {article['title']}",
            "",
            f"- PMID: {article['pmid']}",
            f"- Source: {article['record_url']}",
            "",
            "**Abstract**",
            "",
            article.get("abstract") or "No abstract available.",
            "",
        ])

    report_directory = PROJECT_ROOT / "data" / "reports"
    report_directory.mkdir(parents=True, exist_ok=True)

    # Use the content hash for a safe, reproducible output filename.
    destination = report_directory / f"brca1-{bundle_sha256}.md"
    destination.write_text("\n".join(lines), encoding="utf-8")

    return destination


def main():
    parser = argparse.ArgumentParser(
        description="Create a BRCA1 report from a saved evidence bundle."
    )
    parser.add_argument("bundle", help="Path to the evidence bundle JSON.")
    args = parser.parse_args()

    try:
        destination = create_report(args.bundle)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Report could not be created: {exc}\n")

    print(f"Report saved: {destination}")


if __name__ == "__main__":
    main()