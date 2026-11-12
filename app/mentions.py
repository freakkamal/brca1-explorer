"""Find literal text mentions in one saved BRCA1 literature bundle."""

import re

from app.compare import load_bundle


def find_mentions(filename, query):
    query = query.strip()
    if not query or len(query) > 120:
        raise ValueError("Enter a search term between 1 and 120 characters.")

    # Treat punctuation literally and avoid matching inside longer words.
    pattern = re.compile(r"(?<!\w)" + re.escape(query) + r"(?!\w)", re.I)
    bundle = load_bundle(filename)  # Also checks the referenced raw files.
    matches = []

    for article in bundle["articles"].values():
        title = article["title"]
        title_match = bool(pattern.search(title))
        abstract = article["abstract"] or ""
        passages = re.split(r"(?<=[.!?])\s+|\n+", abstract)
        hits = [p.strip() for p in passages if pattern.search(p)]

        if title_match or hits:
            matches.append({
                "pmid": article["pmid"],
                "title": title,
                "title_match": title_match,
                "passages": hits,
            })

    return {
        "filename": bundle["filename"],
        "sha256": bundle["sha256"],
        "article_count": len(bundle["articles"]),
        "matches": matches,
    }