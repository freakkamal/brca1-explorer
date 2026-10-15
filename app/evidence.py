"""Create a BRCA1 evidence bundle from retrieved source records."""
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import subprocess
import tempfile
from uuid import uuid4

from app import ncbi, pubmed, storage, uniprot


def git_provenance():
    """Record the checked-out commit and uncommitted-change status."""
    def run_git(*arguments):
        return subprocess.run(
            ["git", *arguments],
            cwd=storage.PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()

    return {
        "commit": run_git("rev-parse", "HEAD"),
        "working_tree_dirty": bool(
            run_git("status", "--porcelain", "--untracked-files=all")
        ),
    }


def verified_raw_file(source, metadata):
    """Check a saved raw response against its retrieval checksum."""
    digest = metadata["response_sha256"]
    if not isinstance(digest, str) or not re.fullmatch(
        r"[0-9a-f]{64}", digest
    ):
        raise ValueError("Missing or invalid response checksum.")

    relative = (
        f"data/raw/{source}/{digest}{storage.SOURCE_FORMATS[source]}"
    )
    content = (storage.PROJECT_ROOT / relative).read_bytes()

    if hashlib.sha256(content).hexdigest() != digest:
        raise RuntimeError(f"Checksum mismatch for {source}.")

    return {
        "source": source,
        "path": relative,
        "sha256": digest,
        "size_bytes": len(content),
    }


def create_brca1_bundle():
    """Retrieve evidence and save a complete bundle atomically."""
    code_before = git_provenance()
    started_at = datetime.now(timezone.utc).isoformat()

    protein = uniprot.fetch_brca1_protein()
    gene = ncbi.fetch_brca1_gene()
    literature = pubmed.fetch_brca1_literature()

    raw_files = [
        verified_raw_file("uniprot", protein),
        verified_raw_file("ncbi_gene", gene),
        verified_raw_file(
            "pubmed_search", literature["search_provenance"]
        ),
    ]
    if literature["returned_count"] > 0:
        raw_files.append(
            verified_raw_file(
                "pubmed_fetch", literature["fetch_provenance"]
            )
        )

    code_after = git_provenance()
    if code_before != code_after:
        raise RuntimeError(
            "Git state changed during retrieval. Run the bundle again."
        )

    bundle_id = uuid4().hex
    bundle = {
        "schema_version": "1.0",
        "bundle_id": bundle_id,
        "target": "BRCA1",
        "purpose": "Research evidence; not for clinical decisions.",
        "started_at_utc": started_at,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_provenance": code_before,
        "protein": protein,
        "gene": gene,
        "literature": literature,
        "raw_files": raw_files,
    }

    content = json.dumps(
        bundle, indent=2, ensure_ascii=False, allow_nan=False
    ).encode("utf-8")

    directory = storage.PROJECT_ROOT / "data" / "bundles"
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"brca1-{bundle_id}.json"

    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=directory, delete=False
        ) as temporary:
            temporary_path = storage.PROJECT_ROOT.__class__(
                temporary.name
            )
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())

        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return {
        "path": destination.relative_to(
            storage.PROJECT_ROOT
        ).as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "article_count": literature["returned_count"],
        "raw_file_count": len(raw_files),
        "code_provenance": code_before,
    }


if __name__ == "__main__":
    print(json.dumps(create_brca1_bundle(), indent=2))