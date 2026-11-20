"""Run an isolated search demonstration using fictional records."""

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import report, storage
from app.mentions import find_mentions
from app.multi_mentions import search_terms


def run_demo():
    """Exercise the real search functions against temporary sample files."""
    with TemporaryDirectory(prefix="brca1-synthetic-demo-") as folder:
        root = Path(folder)
        raw_directory = root / "data" / "raw" / "synthetic"
        bundle_directory = root / "data" / "bundles"
        raw_directory.mkdir(parents=True)
        bundle_directory.mkdir(parents=True)

        # Numeric identifiers satisfy the existing schema.
        # They are placeholders, not citations to real PubMed articles.
        articles = [
            {
                "pmid": "101",
                "title": "SYNTHETIC: amber and cobalt",
                "abstract": (
                    "Amber and cobalt are example search words. "
                    "This fictional text makes no scientific claim."
                ),
            },
            {
                "pmid": "102",
                "title": "SYNTHETIC: another record",
                "abstract": "This fictional record mentions neither word.",
            },
        ]

        raw_bytes = json.dumps(
            {"synthetic": True, "articles": articles},
            sort_keys=True,
        ).encode("utf-8")
        raw_path = raw_directory / "example.json"
        raw_path.write_bytes(raw_bytes)

        bundle = {
            "target": "BRCA1",
            "synthetic": True,
            "literature": {
                "query": "Synthetic demonstration; no source retrieval",
                "sort": "synthetic",
                "articles": articles,
            },
            "raw_files": [
                {
                    "path": "data/raw/synthetic/example.json",
                    "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                }
            ],
        }

        filename = "brca1-synthetic-demo.json"
        (bundle_directory / filename).write_text(
            json.dumps(bundle, sort_keys=True),
            encoding="utf-8",
        )

        # Only this process uses the temporary root.
        # Both original root values are restored on leaving this block.
        with (
            patch.object(storage, "PROJECT_ROOT", root),
            patch.object(report, "PROJECT_ROOT", root),
        ):
            matching = find_mentions(filename, "amber")
            missing = find_mentions(filename, "zzzz-no-match-123")
            combined = search_terms(
                filename,
                ["amber", "cobalt", "zzzz-no-match-123"],
            )

        if [item["pmid"] for item in matching["matches"]] != ["101"]:
            raise RuntimeError("The matching-search result was unexpected.")

        if missing["matches"]:
            raise RuntimeError("The zero-match search unexpectedly matched.")

        expected_counts = {
            "amber": 1,
            "cobalt": 1,
            "zzzz-no-match-123": 0,
        }
        if combined["matches_per_term"] != expected_counts:
            raise RuntimeError("The per-term counts were unexpected.")

        if combined["unique_articles_matched"] != 1:
            raise RuntimeError("The combined result counted duplicates.")

        if combined["articles"][0]["matched_terms"] != ["amber", "cobalt"]:
            raise RuntimeError("The combined result lost a matching term.")

        print("SYNTHETIC DEMONSTRATION - not scientific evidence")
        print("Record ID 101 is a placeholder, not a PubMed citation.")
        print("Matching search: amber -> record 101")
        print("Zero-match search: zzzz-no-match-123 -> no records")
        print("Matches per term:", combined["matches_per_term"])
        print("Distinct records:", combined["unique_articles_matched"])
        print("Record 101 matched terms: amber, cobalt")

    print("Temporary demonstration files removed.")
    print("All demonstration checks passed.")


if __name__ == "__main__":
    run_demo()