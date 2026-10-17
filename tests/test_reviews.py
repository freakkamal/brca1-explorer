"""Tests for reviews linked to exact summary versions."""

import hashlib
import json

import pytest

from app import report, reviews, storage, summaries


@pytest.fixture
def review_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(report, "PROJECT_ROOT", tmp_path)

    raw = storage.save_raw_response(
        "uniprot", b'{"example": "test evidence"}'
    )
    bundle = {
        "target": "BRCA1",
        "bundle_id": "review-test",
        "literature": {
            "articles": [{"pmid": "123456"}, {"pmid": "234567"}],
        },
        "raw_files": [{"source": "uniprot", **raw}],
    }

    bundle_path = tmp_path / "data/bundles/brca1-test.json"
    bundle_path.parent.mkdir(parents=True)
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    digest = hashlib.sha256(bundle_path.read_bytes()).hexdigest()

    draft = tmp_path / "draft.md"
    draft.write_text(
        "First finding. PMID: 123456\nSecond finding. PMID: 234567",
        encoding="utf-8",
    )
    summary_path = summaries.import_summary(bundle_path, draft, digest)

    return summary_path, bundle_path, tmp_path / raw["path"]


def test_partial_review_preserves_summary(review_inputs):
    summary_path, bundle_path, raw_path = review_inputs
    original = summary_path.read_bytes()

    destination = reviews.save_review(
        summary_path,
        reviewer="Test reviewer",
        decision="in_progress",
        notes="Checked the first test finding against its abstract.",
        checked_pmids=["123456"],
    )
    saved = json.loads(destination.read_text(encoding="utf-8"))

    assert saved["decision"] == "in_progress"
    assert saved["scope"] == "selected_claims"
    assert saved["checked_pmids"] == ["123456"]
    assert saved["summary_file_sha256"] == hashlib.sha256(
        original
    ).hexdigest()
    assert summary_path.read_bytes() == original


def test_partial_review_cannot_mark_whole_summary_reviewed(review_inputs):
    summary_path, bundle_path, raw_path = review_inputs

    with pytest.raises(ValueError, match="Reviewed requires"):
        reviews.save_review(
            summary_path,
            "Test reviewer",
            "reviewed",
            "Only one finding checked.",
            ["123456"],
            scope="whole_summary",
        )

    assert not (storage.PROJECT_ROOT / "data/reviews").exists()


def test_whole_summary_review_can_be_recorded(review_inputs):
    summary_path, bundle_path, raw_path = review_inputs

    destination = reviews.save_review(
        summary_path,
        "Test reviewer",
        "reviewed",
        "Checked both example findings and all summary statements.",
        ["123456", "234567"],
        scope="whole_summary",
    )
    saved = json.loads(destination.read_text(encoding="utf-8"))

    assert saved["decision"] == "reviewed"
    assert saved["scope"] == "whole_summary"


def test_review_rejects_uncited_pmid(review_inputs):
    summary_path, bundle_path, raw_path = review_inputs

    with pytest.raises(ValueError, match="checked PMIDs"):
        reviews.save_review(
            summary_path,
            "Test reviewer",
            "in_progress",
            "Example notes.",
            ["999999"],
        )


def test_review_rejects_changed_summary_text(review_inputs):
    summary_path, bundle_path, raw_path = review_inputs
    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    saved["summary_markdown"] = "Changed finding. PMID: 123456"
    summary_path.write_text(json.dumps(saved), encoding="utf-8")

    with pytest.raises(ValueError, match="Summary text checksum mismatch"):
        reviews.save_review(
            summary_path,
            "Test reviewer",
            "in_progress",
            "Example notes.",
            ["123456"],
        )


def test_review_rejects_changed_bundle(review_inputs):
    summary_path, bundle_path, raw_path = review_inputs
    bundle_path.write_bytes(bundle_path.read_bytes() + b"\n")

    with pytest.raises(ValueError, match="Bundle checksum mismatch"):
        reviews.save_review(
            summary_path,
            "Test reviewer",
            "in_progress",
            "Example notes.",
            ["123456"],
        )


def test_review_rejects_corrupted_raw_evidence(review_inputs):
    summary_path, bundle_path, raw_path = review_inputs
    raw_path.write_bytes(b"corrupted evidence")

    with pytest.raises(ValueError, match="Checksum mismatch"):
        reviews.save_review(
            summary_path,
            "Test reviewer",
            "in_progress",
            "Example notes.",
            ["123456"],
        )


def test_new_review_preserves_previous_record(review_inputs):
    summary_path, bundle_path, raw_path = review_inputs

    first = reviews.save_review(
        summary_path,
        "Test reviewer",
        "in_progress",
        "Checked the first finding.",
        ["123456"],
    )
    original = first.read_bytes()

    second = reviews.save_review(
        summary_path,
        "Test reviewer",
        "changes_requested",
        "The first finding needs clearer wording.",
        ["123456"],
    )

    assert first != second
    assert first.read_bytes() == original
    assert second.is_file()