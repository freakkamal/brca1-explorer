"""Test comparisons of saved evidence bundles."""

import hashlib
import json

import pytest

from app import compare, report, storage


@pytest.fixture
def make_bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(report, "PROJECT_ROOT", tmp_path)

    raw = tmp_path / "data/raw/uniprot/example.json"
    raw.parent.mkdir(parents=True)
    raw.write_bytes(b'{"example": true}')

    directory = tmp_path / "data/bundles"
    directory.mkdir(parents=True)

    def create(filename, articles, query="BRCA1[Title/Abstract]"):
        bundle = {
            "target": "BRCA1",
            "literature": {
                "query": query,
                "sort": "relevance",
                "articles": articles,
            },
            "raw_files": [{
                "path": "data/raw/uniprot/example.json",
                "sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
            }],
        }
        path = directory / filename
        path.write_text(json.dumps(bundle), encoding="utf-8")
        return path

    return create


def article(pmid, title="Example title", abstract="Example abstract"):
    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
    }


def test_article_membership(make_bundle):
    make_bundle("brca1-before.json", [article("1"), article("2")])
    make_bundle("brca1-after.json", [article("2"), article("3")])

    result = compare.compare_bundles(
        "brca1-before.json", "brca1-after.json"
    )

    assert result["counts"] == {
        "baseline_articles": 2,
        "comparison_articles": 2,
        "only_in_comparison": 1,
        "only_in_baseline": 1,
        "shared": 1,
        "shared_with_text_changes": 0,
    }
    assert result["shared_pmids"] == ["2"]
    assert result["only_in_comparison"][0]["pmid"] == "3"
    assert result["only_in_baseline"][0]["pmid"] == "1"


def test_shared_text_changes(make_bundle):
    make_bundle("brca1-before.json", [article("1")])
    make_bundle(
        "brca1-after.json",
        [article("1", title="Changed title", abstract=None)],
    )

    result = compare.compare_bundles(
        "brca1-before.json", "brca1-after.json"
    )

    assert result["counts"]["shared_with_text_changes"] == 1
    assert result["shared_text_changes"][0]["changed_fields"] == [
        "title", "abstract"
    ]


def test_same_bundle_has_no_differences(make_bundle):
    make_bundle("brca1-test.json", [article("1")])

    result = compare.compare_bundles(
        "brca1-test.json", "brca1-test.json"
    )

    assert result["counts"]["shared"] == 1
    assert result["only_in_comparison"] == []
    assert result["only_in_baseline"] == []
    assert result["shared_text_changes"] == []


def test_empty_article_lists(make_bundle):
    make_bundle("brca1-before.json", [])
    make_bundle("brca1-after.json", [])

    result = compare.compare_bundles(
        "brca1-before.json", "brca1-after.json"
    )

    assert all(value == 0 for value in result["counts"].values())


def test_different_search_query_is_flagged(make_bundle):
    make_bundle("brca1-before.json", [article("1")])
    make_bundle(
        "brca1-after.json",
        [article("1")],
        query="BRCA1 AND DNA repair",
    )

    result = compare.compare_bundles(
        "brca1-before.json", "brca1-after.json"
    )

    assert (
        "Search query or ordering differs between these bundles."
        in result["limitations"]
    )


def test_duplicate_pmids_are_rejected(make_bundle):
    make_bundle("brca1-test.json", [article("1"), article("1")])

    with pytest.raises(ValueError, match="Duplicate PMID"):
        compare.load_bundle("brca1-test.json")


def test_invalid_pmid_is_rejected(make_bundle):
    make_bundle("brca1-test.json", [article("not-a-pmid")])

    with pytest.raises(ValueError, match="Invalid article PMID"):
        compare.load_bundle("brca1-test.json")


def test_corrupt_raw_file_is_rejected(make_bundle):
    make_bundle("brca1-test.json", [article("1")])
    raw = storage.PROJECT_ROOT / "data/raw/uniprot/example.json"
    raw.write_bytes(b"changed after the bundle was saved")

    with pytest.raises(ValueError, match="Checksum mismatch"):
        compare.load_bundle("brca1-test.json")


def test_path_traversal_is_rejected(make_bundle):
    make_bundle("brca1-test.json", [article("1")])

    with pytest.raises(ValueError, match="Bundle not found"):
        compare.load_bundle("../brca1-test.json")

@pytest.fixture
def web_client():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        yield client


def test_comparison_page_offers_both_selectors(make_bundle, web_client):
    make_bundle("brca1-first.json", [])
    make_bundle("brca1-second.json", [])

    response = web_client.get("/compare-bundles")

    assert response.status_code == 200
    assert 'name="baseline"' in response.text
    assert 'name="comparison"' in response.text
    assert "brca1-first.json" in response.text
    assert "brca1-second.json" in response.text
    assert "Comparison results" not in response.text


def test_comparison_page_shows_articles_on_correct_side(make_bundle, web_client):
    make_bundle("brca1-first.json", [
        article("101", title="Baseline study"),
        article("202", title="Shared study"),
    ])
    make_bundle("brca1-second.json", [
        article("202", title="Shared study"),
        article("303", title="Follow-up study", abstract="Measured A < B."),
    ])

    response = web_client.get("/compare-bundles", params={
        "baseline": "brca1-first.json",
        "comparison": "brca1-second.json",
    })

    assert response.status_code == 200
    html = response.text
    newer = html.split("<h2>Articles only in comparison</h2>", 1)[1].split("</section>", 1)[0]
    older = html.split("<h2>Articles only in baseline</h2>", 1)[1].split("</section>", 1)[0]

    assert "Follow-up study" in newer and "Baseline study" not in newer
    assert "Baseline study" in older and "Follow-up study" not in older
    assert 'href="https://pubmed.ncbi.nlm.nih.gov/303/"' in newer
    assert "Measured A &lt; B." in newer
    assert "No text changes among shared articles." in html


def test_comparison_page_rejects_missing_bundle(make_bundle, web_client):
    make_bundle("brca1-first.json", [])

    response = web_client.get("/compare-bundles", params={
        "baseline": "brca1-first.json",
        "comparison": "brca1-missing.json",
    })

    assert response.status_code == 404
    assert "Comparison results" not in response.text

def test_mentions_return_title_and_only_matching_passage(make_bundle):
    from app.mentions import find_mentions

    make_bundle("brca1-mentions.json", [
        article("101", title="Aspirin study",
                abstract="Background sentence. ASPIRIN was measured."),
        article("202", title="Other record", abstract=None),
    ])
    result = find_mentions("brca1-mentions.json", "aspirin")

    assert result["article_count"] == 2
    assert [m["pmid"] for m in result["matches"]] == ["101"]
    assert result["matches"][0]["title_match"] is True
    assert result["matches"][0]["passages"] == ["ASPIRIN was measured."]


def test_mentions_do_not_match_inside_longer_words(make_bundle):
    from app.mentions import find_mentions

    make_bundle("brca1-mentions.json", [
        article("101", title="BRCA10 example", abstract=None),
    ])
    assert find_mentions("brca1-mentions.json", "BRCA1")["matches"] == []


def test_mentions_page_links_source_and_escapes_passage(make_bundle, web_client):
    make_bundle("brca1-mentions.json", [
        article("101", title="Example", abstract="Aspirin: A < B."),
    ])
    response = web_client.get("/literature-mentions", params={
        "bundle": "brca1-mentions.json", "q": "aspirin",
    })

    assert response.status_code == 200
    assert "1 of 1 saved articles" in response.text
    assert 'href="https://pubmed.ncbi.nlm.nih.gov/101/"' in response.text
    assert "Aspirin: A &lt; B." in response.text

def test_offline_literature_export_example(make_bundle):
    """Run the real search and JSON export on two synthetic articles."""
    import hashlib

    from fastapi.testclient import TestClient
    from app.main import app

    bundle_path = make_bundle(
        "brca1-synthetic-demo.json",
        [
            article("101", "Synthetic article A", "GPX4 is the example search term."),
            article("102", "Synthetic article B", "This example discusses DNA repair."),
        ],
    )
    expected_hash = hashlib.sha256(bundle_path.read_bytes()).hexdigest()

    with TestClient(app) as client:
        for term, expected_ids in [
            ("GPX4", ["101"]),
            ("zzzz-no-match-123", []),
        ]:
            response = client.get(
                "/download-literature-mentions",
                params={"bundle": bundle_path.name, "q": term},
            )
            assert response.status_code == 200, response.text

            result = response.json()
            assert result["query"] == term
            assert result["bundle_filename"] == bundle_path.name
            assert result["bundle_sha256"] == expected_hash
            assert result["articles_searched"] == 2
            assert result["articles_matched"] == len(expected_ids)
            assert [item["pmid"] for item in result["matches"]] == expected_ids

            if expected_ids:
                assert result["matches"][0]["passages"] == [
                    "GPX4 is the example search term."
                ]

def test_export_refuses_changed_raw_file(make_bundle):
    """The same export succeeds before a raw file changes and fails after."""
    from fastapi.testclient import TestClient
    from app.main import app

    bundle_path = make_bundle(
        "brca1-integrity-demo.json",
        [article("101", "Synthetic article", "GPX4 is the example term.")],
    )
    params = {"bundle": bundle_path.name, "q": "GPX4"}

    with TestClient(app) as client:
        before = client.get("/download-literature-mentions", params=params)
        assert before.status_code == 200, before.text
        assert before.json()["articles_matched"] == 1

        # Change only the temporary raw file. Keep the bundle hash record intact.
        raw_path = bundle_path.parents[1] / "raw" / "uniprot" / "example.json"
        assert raw_path.is_file()
        raw_path.write_bytes(b'{"example": false}')

        after = client.get("/download-literature-mentions", params=params)
        assert after.status_code == 400, after.text
        assert "checksum mismatch" in after.json()["detail"].lower()
        assert "content-disposition" not in after.headers

def test_compare_mentions_groups_matching_pmids(make_bundle):
    from app.compare_mentions import compare_mentions

    first = make_bundle("brca1-first.json", [
        article("101", "Shared GPX4 example"),
        article("102", "GPX4 example in first bundle"),
        article("104", "Unrelated example"),
    ])
    second = make_bundle("brca1-second.json", [
        article("101", "Shared GPX4 example"),
        article("103", "GPX4 example in second bundle"),
        article("104", "Unrelated example"),
    ])

    result = compare_mentions(first.name, second.name, "GPX4")

    assert result["matched_in_both"] == ["101"]
    assert result["matched_only_in_first"] == ["102"]
    assert result["matched_only_in_second"] == ["103"]
    for side in ("first_bundle", "second_bundle"):
        assert result[side]["articles_searched"] == 3
        assert result[side]["articles_matched"] == 2

def test_multi_mentions_counts_each_article_once(make_bundle):
    from app.multi_mentions import search_terms

    bundle = make_bundle("brca1-multi-test.json", [
        article("101", "Cezanne example", "This passage also mentions Ube2S."),
        article("102", "Ube2S example", "Only the second term appears here."),
        article("103", "Unrelated example", "Neither term appears here."),
    ])

    result = search_terms(bundle.name, ["Cezanne", "Ube2S", "no-such-term"])

    assert result["matches_per_term"] == {
        "Cezanne": 1,
        "Ube2S": 2,
        "no-such-term": 0,
    }
    assert result["unique_articles_matched"] == 2
    assert [item["pmid"] for item in result["articles"]] == ["101", "102"]
    assert result["articles"][0]["matched_terms"] == ["Cezanne", "Ube2S"]
    assert result["articles"][1]["matched_terms"] == ["Ube2S"]

def test_reader_can_find_and_use_multi_search(make_bundle):
    from fastapi.testclient import TestClient
    from app.main import app

    bundle = make_bundle("brca1-browser-demo.json", [
        article("101", "Cezanne example", "This passage mentions Ube2S."),
    ])

    with TestClient(app) as client:
        start = client.get("/literature-mentions")
        assert start.status_code == 200
        assert 'href="/multi-mentions"' in start.text

        result = client.get("/multi-mentions", params={
            "bundle": bundle.name,
            "terms": "Cezanne\nUbe2S\nno-such-term",
        })

    assert result.status_code == 200, result.text
    assert "Cezanne: 1" in result.text
    assert "Ube2S: 1" in result.text
    assert "no-such-term: 0" in result.text
    assert "Distinct articles: 1" in result.text
    assert result.text.count('href="https://pubmed.ncbi.nlm.nih.gov/101/"') == 1
    assert "Matched terms: Cezanne, Ube2S" in result.text