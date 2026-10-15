"""Offline tests for evidence bundle creation."""
import hashlib
import json

import pytest

from app import evidence, storage


@pytest.fixture
def sample_sources(monkeypatch):
    def saved(source, content):
        raw = storage.save_raw_response(source, content)
        return {"response_sha256": raw["sha256"]}

    protein = saved("uniprot", b'{"sample": "protein"}')
    gene = saved("ncbi_gene", b'{"sample": "gene"}')
    search = saved("pubmed_search", b'{"sample": "search"}')
    fetch = saved("pubmed_fetch", b"<sample />")

    literature = {
        "returned_count": 1,
        "articles": [{"pmid": "111", "title": "Fictional test article"}],
        "search_provenance": search,
        "fetch_provenance": fetch,
    }

    monkeypatch.setattr(
        evidence.uniprot, "fetch_brca1_protein", lambda: protein
    )
    monkeypatch.setattr(
        evidence.ncbi, "fetch_brca1_gene", lambda: gene
    )
    monkeypatch.setattr(
        evidence.pubmed, "fetch_brca1_literature", lambda: literature
    )
    monkeypatch.setattr(
        evidence,
        "git_provenance",
        lambda: {"commit": "a" * 40, "working_tree_dirty": False},
    )
    return protein, gene, literature


def test_bundle_saved_with_verified_references(sample_sources):
    result = evidence.create_brca1_bundle()
    path = storage.PROJECT_ROOT / result["path"]
    content = path.read_bytes()
    bundle = json.loads(content)

    assert result["sha256"] == hashlib.sha256(content).hexdigest()
    assert result["article_count"] == 1
    assert result["raw_file_count"] == 4
    assert bundle["target"] == "BRCA1"
    assert bundle["code_provenance"]["commit"] == "a" * 40
    assert bundle["protein"] == sample_sources[0]
    assert bundle["gene"] == sample_sources[1]
    assert bundle["literature"] == sample_sources[2]

    for raw in bundle["raw_files"]:
        saved_bytes = (storage.PROJECT_ROOT / raw["path"]).read_bytes()
        assert hashlib.sha256(saved_bytes).hexdigest() == raw["sha256"]
        assert len(saved_bytes) == raw["size_bytes"]


def test_empty_literature_needs_no_fetch_file(sample_sources):
    literature = sample_sources[2]
    literature["returned_count"] = 0
    literature["articles"] = []
    literature["fetch_provenance"] = {
        "api_url": None,
        "retrieved_at_utc": None,
        "response_sha256": None,
    }

    result = evidence.create_brca1_bundle()

    assert result["article_count"] == 0
    assert result["raw_file_count"] == 3


def test_corrupted_raw_file_blocks_bundle(sample_sources):
    digest = sample_sources[0]["response_sha256"]
    path = storage.PROJECT_ROOT / f"data/raw/uniprot/{digest}.json"
    path.write_bytes(b"damaged")

    with pytest.raises(RuntimeError, match="Checksum mismatch"):
        evidence.create_brca1_bundle()

    assert not list(storage.PROJECT_ROOT.glob("data/bundles/*.json"))


def test_git_change_blocks_bundle(monkeypatch, sample_sources):
    states = iter([
        {"commit": "a" * 40, "working_tree_dirty": False},
        {"commit": "b" * 40, "working_tree_dirty": False},
    ])
    monkeypatch.setattr(
        evidence, "git_provenance", lambda: next(states)
    )

    with pytest.raises(RuntimeError, match="Git state changed"):
        evidence.create_brca1_bundle()

    assert not list(storage.PROJECT_ROOT.glob("data/bundles/*.json"))


def test_failed_bundle_write_leaves_no_file(monkeypatch, sample_sources):
    def failed_replace(*args, **kwargs):
        raise OSError("Simulated disk failure")

    monkeypatch.setattr(evidence.os, "replace", failed_replace)

    with pytest.raises(OSError, match="Simulated disk failure"):
        evidence.create_brca1_bundle()

    directory = storage.PROJECT_ROOT / "data/bundles"
    assert list(directory.iterdir()) == []