"""Search PubMed for BRCA1 article identifiers."""
from datetime import datetime, timezone
import hashlib

import httpx

SEARCH_URL = (
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
)
QUERY = "BRCA1[Title/Abstract]"
MAX_RESULTS = 10


def search_brca1_articles():
    """Return unique PMIDs and search provenance."""
    try:
        response = httpx.get(
            SEARCH_URL,
            params={
                "db": "pubmed",
                "term": QUERY,
                "retmode": "json",
                "retmax": MAX_RESULTS,
                "sort": "relevance",
                "tool": "brca1_evidence_explorer",
            },
            timeout=30,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise RuntimeError(
            "PubMed search timed out. Try again later."
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"PubMed returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Could not connect to PubMed.") from exc

    retrieved_at = datetime.now(timezone.utc).isoformat()

    try:
        payload = response.json()
        if not isinstance(payload, dict) or "error" in payload:
            raise ValueError("Invalid search response.")

        result = payload["esearchresult"]
        if not isinstance(result, dict):
            raise ValueError("Invalid search result.")
        if "ERROR" in result or "errorlist" in result:
            raise ValueError("PubMed reported a search error.")

        total_count = int(result["count"])
        identifiers = result["idlist"]

        if total_count < 0 or not isinstance(identifiers, list):
            raise ValueError("Invalid count or identifier list.")

        if any(
            not isinstance(pmid, str)
            or not pmid.isascii()
            or not pmid.isdigit()
            or int(pmid) <= 0
            for pmid in identifiers
        ):
            raise ValueError("Invalid PMID.")

        pmids = list(dict.fromkeys(identifiers))[:MAX_RESULTS]

        if len(pmids) > total_count:
            raise ValueError("Inconsistent result count.")
        if total_count > 0 and not pmids:
            raise ValueError("Missing search identifiers.")

    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(
            "PubMed returned an invalid or unexpected search response."
        ) from exc

    return {
        "evidence_type": "retrieved",
        "source": "PubMed",
        "query": QUERY,
        "sort": "relevance",
        "total_matching_records": total_count,
        "returned_count": len(pmids),
        "pmids": pmids,
        "api_url": str(response.request.url),
        "retrieved_at_utc": retrieved_at,
        "response_sha256": hashlib.sha256(
            response.content
        ).hexdigest(),
    }
# Article detail retrieval
import xml.etree.ElementTree as ET

FETCH_URL = (
    "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
)


def _element_text(element):
    """Keep text inside nested XML tags, including italics."""
    if element is None:
        return None
    return "".join(element.itertext()).strip() or None


def fetch_article_details(pmids):
    """Fetch up to 10 unique PubMed records in one request."""
    if not isinstance(pmids, list) or any(
        not isinstance(pmid, str)
        or not pmid.isascii()
        or not pmid.isdigit()
        or int(pmid) <= 0
        for pmid in pmids
    ):
        raise ValueError("PMIDs must be a list of positive numeric strings.")

    requested = list(dict.fromkeys(pmids))
    if len(requested) > MAX_RESULTS:
        raise ValueError("Request no more than 10 unique PMIDs.")

    if not requested:
        return {
            "source": "PubMed",
            "articles": [],
            "api_url": None,
            "retrieved_at_utc": None,
            "response_sha256": None,
        }

    try:
        response = httpx.get(
            FETCH_URL,
            params={
                "db": "pubmed",
                "id": ",".join(requested),
                "retmode": "xml",
                "tool": "brca1_evidence_explorer",
            },
            timeout=30,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise RuntimeError("PubMed article retrieval timed out.") from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(
            f"PubMed returned HTTP {exc.response.status_code}."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError("Could not connect to PubMed.") from exc

    retrieved_at = datetime.now(timezone.utc).isoformat()

    try:
        root = ET.fromstring(response.content)
        if root.tag != "PubmedArticleSet":
            raise ValueError("Unexpected XML response.")
        if root.find(".//ERROR") is not None:
            raise ValueError("PubMed reported an error.")

        records = {}
        for record in root:
            if record.tag == "PubmedArticle":
                document = record.find("MedlineCitation")
                article = record.find("MedlineCitation/Article")
            elif record.tag == "PubmedBookArticle":
                document = record.find("BookDocument")
                article = document
            else:
                raise ValueError("Unsupported record type.")

            if document is None or article is None:
                raise ValueError("Missing article data.")

            pmid = _element_text(document.find("PMID"))
            title = _element_text(article.find("ArticleTitle"))

            if pmid not in requested or not title:
                raise ValueError("Unexpected PMID or missing title.")
            if pmid in records:
                raise ValueError("Duplicate record returned.")

            sections = []
            for section in article.findall("Abstract/AbstractText"):
                text = _element_text(section)
                if text:
                    label = section.get("Label")
                    sections.append(
                        f"{label}: {text}" if label else text
                    )

            abstract = "\n\n".join(sections) or None
            records[pmid] = {
                "evidence_type": "retrieved",
                "source": "PubMed",
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "abstract_available": abstract is not None,
                "record_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }

        if set(records) != set(requested):
            raise ValueError("Some requested records were not returned.")

    except (ET.ParseError, ValueError) as exc:
        raise RuntimeError(
            "PubMed returned invalid or incomplete article data."
        ) from exc

    return {
        "source": "PubMed",
        "articles": [records[pmid] for pmid in requested],
        "api_url": str(response.request.url),
        "retrieved_at_utc": retrieved_at,
        "response_sha256": hashlib.sha256(
            response.content
        ).hexdigest(),
    }
def fetch_brca1_literature():
    """Search BRCA1 and retrieve details in search-result order."""
    search = search_brca1_articles()
    details = fetch_article_details(search["pmids"])

    return {
        "evidence_type": "retrieved",
        "source": "PubMed",
        "query": search["query"],
        "sort": search["sort"],
        "total_matching_records": search["total_matching_records"],
        "returned_count": len(details["articles"]),
        "articles": details["articles"],
        "search_provenance": {
            "api_url": search["api_url"],
            "retrieved_at_utc": search["retrieved_at_utc"],
            "response_sha256": search["response_sha256"],
        },
        "fetch_provenance": {
            "api_url": details["api_url"],
            "retrieved_at_utc": details["retrieved_at_utc"],
            "response_sha256": details["response_sha256"],
        },
    }