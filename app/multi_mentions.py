"""Find articles mentioning any of several user-supplied terms."""

import argparse
import json

from app.mentions import find_mentions


def search_terms(bundle, terms):
    unique_terms = []
    seen = set()

    for raw in terms:
        term = raw.strip()
        if not 1 <= len(term) <= 120:
            raise ValueError("Each search term must contain 1 to 120 characters.")
        if term.casefold() not in seen:
            seen.add(term.casefold())
            unique_terms.append(term)

    if not 1 <= len(unique_terms) <= 10:
        raise ValueError("Enter between 1 and 10 distinct search terms.")

    by_pmid = {}
    counts = {}
    digest = None

    for term in unique_terms:
        result = find_mentions(bundle, term)
        if digest is None:
            digest = result["sha256"]
        elif result["sha256"] != digest:
            raise ValueError("The selected bundle changed during the search.")

        counts[term] = len(result["matches"])
        for item in result["matches"]:
            pmid = item["pmid"]
            if pmid not in by_pmid:
                by_pmid[pmid] = {
                    "pmid": pmid,
                    "title": item["title"],
                    "matched_terms": [],
                }
            by_pmid[pmid]["matched_terms"].append(term)

    return {
        "bundle_filename": bundle,
        "bundle_sha256": digest,
        "matches_per_term": counts,
        "unique_articles_matched": len(by_pmid),
        "articles": [by_pmid[p] for p in sorted(by_pmid, key=int)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", help="Saved bundle filename")
    parser.add_argument("terms", nargs="+", help="Quote phrases containing spaces")
    args = parser.parse_args()

    try:
        result = search_terms(args.bundle, args.terms)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"Search failed: {exc}\n")

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()