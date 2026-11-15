"""Compare matching PubMed IDs across two saved evidence bundles."""

import argparse
import json

from app.mentions import find_mentions


def compare_mentions(first_bundle, second_bundle, query):
    query = query.strip()
    if first_bundle == second_bundle:
        raise ValueError("Choose two different bundle files.")

    first = find_mentions(first_bundle, query)
    second = find_mentions(second_bundle, query)

    first_ids = {item["pmid"] for item in first["matches"]}
    second_ids = {item["pmid"] for item in second["matches"]}

    return {
        "query": query,
        "first_bundle": {
            "filename": first["filename"],
            "sha256": first["sha256"],
            "articles_searched": first["article_count"],
            "articles_matched": len(first_ids),
        },
        "second_bundle": {
            "filename": second["filename"],
            "sha256": second["sha256"],
            "articles_searched": second["article_count"],
            "articles_matched": len(second_ids),
        },
        "matched_in_both": sorted(first_ids & second_ids, key=int),
        "matched_only_in_first": sorted(first_ids - second_ids, key=int),
        "matched_only_in_second": sorted(second_ids - first_ids, key=int),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("first_bundle", help="First saved bundle filename")
    parser.add_argument("second_bundle", help="Second saved bundle filename")
    parser.add_argument("query", help="Word or phrase to search for")
    args = parser.parse_args()

    try:
        result = compare_mentions(args.first_bundle, args.second_bundle, args.query)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Comparison failed: {exc}\n")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()