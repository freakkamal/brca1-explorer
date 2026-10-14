"""Offline tests for PubMed article parsing."""
import hashlib

import httpx
import pytest

from app import pubmed


SAMPLE_XML = b"""
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>111</PMID>
      <Article>
        <ArticleTitle>Example <i>BRCA1</i> study.</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">First section.</AbstractText>
          <AbstractText Label="RESULTS">Second section.</AbstractText>
        </Abstract>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>222</PMID>
      <Article>
        <ArticleTitle>Example without an abstract.</ArticleTitle>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


def mock_fetch(monkeypatch, content=SAMPLE_XML):
    def fake_get(url, *, params, timeout):
        assert url == pubmed.FETCH_URL
        assert params["db"] == "pubmed"
        assert params["retmode"] == "xml"
        return httpx.Response(
            200,
            content=content,
            request=httpx.Request("GET", url, params=params),
        )

    monkeypatch.setattr(pubmed.httpx, "get", fake_get)


def test_title_sections_and_checksum(monkeypatch):
    mock_fetch(monkeypatch)

    result = pubmed.fetch_article_details(["111", "222"])
    article = result["articles"][0]

    assert article["title"] == "Example BRCA1 study."
    assert article["abstract"] == (
        "BACKGROUND: First section.\n\nRESULTS: Second section."
    )
    assert article["abstract_available"] is True
    assert result["response_sha256"] == hashlib.sha256(
        SAMPLE_XML
    ).hexdigest()


def test_missing_abstract_keeps_article(monkeypatch):
    mock_fetch(monkeypatch)

    result = pubmed.fetch_article_details(["111", "222"])
    article = result["articles"][1]

    assert article["pmid"] == "222"
    assert article["abstract"] is None
    assert article["abstract_available"] is False


def test_requested_order_and_unique_results(monkeypatch):
    mock_fetch(monkeypatch)

    result = pubmed.fetch_article_details(["222", "111", "222"])

    assert [a["pmid"] for a in result["articles"]] == ["222", "111"]


@pytest.mark.parametrize("content", [
    b"<broken",
    b"<PubmedArticleSet></PubmedArticleSet>",
    SAMPLE_XML.replace(b"<PMID>111</PMID>", b"<PMID>999</PMID>"),
])
def test_invalid_or_incomplete_records(monkeypatch, content):
    mock_fetch(monkeypatch, content)

    with pytest.raises(RuntimeError, match="invalid or incomplete"):
        pubmed.fetch_article_details(["111", "222"])


def test_empty_input_makes_no_request(monkeypatch):
    def unexpected_request(*args, **kwargs):
        pytest.fail("Empty input must not call PubMed.")

    monkeypatch.setattr(pubmed.httpx, "get", unexpected_request)

    result = pubmed.fetch_article_details([])

    assert result["articles"] == []
    assert result["retrieved_at_utc"] is None