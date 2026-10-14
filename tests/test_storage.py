"""Test raw-response storage using temporary directories."""
import hashlib

import pytest

from app import storage


@pytest.fixture(autouse=True)
def isolated_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "PROJECT_ROOT", tmp_path)


def test_saves_exact_bytes_and_metadata(tmp_path):
    content = b'{"gene": "BRCA1"}\r\n'
    digest = hashlib.sha256(content).hexdigest()

    result = storage.save_raw_response("uniprot", content)

    assert result == {
        "path": f"data/raw/uniprot/{digest}.json",
        "sha256": digest,
        "size_bytes": len(content),
    }
    assert (tmp_path / result["path"]).read_bytes() == content


def test_identical_response_reuses_file(tmp_path):
    content = b"<PubmedArticleSet />"

    first = storage.save_raw_response("pubmed_fetch", content)
    second = storage.save_raw_response("pubmed_fetch", content)

    assert first == second
    directory = tmp_path / "data/raw/pubmed_fetch"
    assert list(directory.iterdir()) == [tmp_path / first["path"]]


def test_corrupted_file_is_rejected(tmp_path):
    content = b'{"gene": "BRCA1"}'
    result = storage.save_raw_response("ncbi_gene", content)
    saved_file = tmp_path / result["path"]
    saved_file.write_bytes(b"damaged")

    with pytest.raises(RuntimeError, match="failed verification"):
        storage.save_raw_response("ncbi_gene", content)

    assert saved_file.read_bytes() == b"damaged"


def test_unknown_source_is_rejected():
    with pytest.raises(ValueError, match="Unknown source"):
        storage.save_raw_response("../outside", b"test")


def test_text_input_is_rejected():
    with pytest.raises(TypeError, match="must be bytes"):
        storage.save_raw_response("uniprot", "text")


def test_failed_save_cleans_temporary_file(monkeypatch, tmp_path):
    def failed_replace(*args, **kwargs):
        raise OSError("Simulated disk failure")

    monkeypatch.setattr(storage.os, "replace", failed_replace)

    with pytest.raises(OSError, match="Simulated disk failure"):
        storage.save_raw_response("pubmed_search", b"{}")

    directory = tmp_path / "data/raw/pubmed_search"
    assert list(directory.iterdir()) == []