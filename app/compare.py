"""Compare PubMed articles in two verified saved evidence bundles."""

import argparse
import hashlib
import json
import re

from app import report, storage


def load_bundle(filename):
    """Read and verify a bundle selected by its filename."""
    directory = (storage.PROJECT_ROOT / "data/bundles").resolve()
    available = {
        path.name: path
        for path in directory.glob("brca1-*.json")
        if path.is_file() and path.resolve().is_relative_to(directory)
    }

    if filename not in available:
        raise ValueError(f"Bundle not found: {filename}")

    content = available[filename].read_bytes()
    bundle = json.loads(content)

    if not isinstance(bundle, dict) or bundle.get("target") != "BRCA1":
        raise ValueError("Expected a BRCA1 evidence bundle.")

    verified_count = report.verify_raw_files(bundle)

    literature = bundle["literature"]
    if not isinstance(literature, dict):
        raise ValueError("Invalid literature record.")

    for field in ("query", "sort"):
        if not isinstance(literature[field], str):
            raise ValueError(f"Invalid literature field: {field}")

    articles = literature["articles"]
    if not isinstance(articles, list):
        raise ValueError("Articles must be a list.")

    indexed = {}
    for article in articles:
        if not isinstance(article, dict):
            raise ValueError("Invalid article record.")

        pmid = article["pmid"]
        if not isinstance(pmid, str) or not re.fullmatch(
            r"[1-9][0-9]*", pmid
        ):
            raise ValueError("Invalid article PMID.")

        if pmid in indexed:
            raise ValueError(f"Duplicate PMID in bundle: {pmid}")

        if (
            not isinstance(article["title"], str)
            or not article["title"].strip()
        ):
            raise ValueError("Article title is missing.")

        abstract = article.get("abstract")
        if abstract is not None and not isinstance(abstract, str):
            raise ValueError("Invalid article abstract.")

        indexed[pmid] = {
            "pmid": pmid,
            "title": article["title"],
            "abstract": abstract,
            "record_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        }

    return {
        "filename": filename,
        "sha256": hashlib.sha256(content).hexdigest(),
        "raw_files_verified": verified_count,
        "query": literature["query"],
        "sort": literature["sort"],
        "articles": indexed,
    }


def compare_bundles(baseline_filename, comparison_filename):
    """Compare article membership and saved title/abstract text."""
    baseline = load_bundle(baseline_filename)
    comparison = load_bundle(comparison_filename)

    before = baseline["articles"]
    after = comparison["articles"]

    before_pmids = set(before)
    after_pmids = set(after)
    shared = before_pmids & after_pmids

    changed = []
    for pmid in sorted(shared, key=int):
        fields = [
            field
            for field in ("title", "abstract")
            if before[pmid][field] != after[pmid][field]
        ]
        if fields:
            changed.append({
                "pmid": pmid,
                "changed_fields": fields,
                "record_url": after[pmid]["record_url"],
            })

    warnings = [
        "Comparison covers saved search results, not all PubMed articles.",
        "An article appearing only in one bundle does not establish "
        "publication, withdrawal, or a change in scientific validity.",
        "Shared PMIDs identify the same records; their saved text may differ.",
        "Checksums establish file integrity, not scientific accuracy.",
    ]
    if (
        baseline["query"] != comparison["query"]
        or baseline["sort"] != comparison["sort"]
    ):
        warnings.append(
            "Search query or ordering differs between these bundles."
        )

    return {
        "target": "BRCA1",
        "baseline": {
            key: value
            for key, value in baseline.items()
            if key != "articles"
        },
        "comparison": {
            key: value
            for key, value in comparison.items()
            if key != "articles"
        },
        "counts": {
            "baseline_articles": len(before),
            "comparison_articles": len(after),
            "only_in_comparison": len(after_pmids - before_pmids),
            "only_in_baseline": len(before_pmids - after_pmids),
            "shared": len(shared),
            "shared_with_text_changes": len(changed),
        },
        "only_in_comparison": [
            after[pmid]
            for pmid in sorted(after_pmids - before_pmids, key=int)
        ],
        "only_in_baseline": [
            before[pmid]
            for pmid in sorted(before_pmids - after_pmids, key=int)
        ],
        "shared_pmids": sorted(shared, key=int),
        "shared_text_changes": changed,
        "limitations": warnings,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compare two verified BRCA1 evidence bundles."
    )
    parser.add_argument("baseline", help="Baseline bundle filename.")
    parser.add_argument("comparison", help="Comparison bundle filename.")
    args = parser.parse_args()

    try:
        result = compare_bundles(args.baseline, args.comparison)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Comparison failed: {exc}\n")

    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()