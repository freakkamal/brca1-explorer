"""Save raw source responses using their SHA-256 hashes."""
import hashlib
import os
from pathlib import Path
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SOURCE_FORMATS = {
    "uniprot": ".json",
    "ncbi_gene": ".json",
    "pubmed_search": ".json",
    "pubmed_fetch": ".xml",
}


def save_raw_response(source, content):
    """Save response bytes atomically and return file metadata."""
    if source not in SOURCE_FORMATS:
        raise ValueError("Unknown source.")
    if not isinstance(content, bytes):
        raise TypeError("Response content must be bytes.")

    digest = hashlib.sha256(content).hexdigest()
    directory = PROJECT_ROOT / "data" / "raw" / source
    directory.mkdir(parents=True, exist_ok=True)

    destination = directory / (
        digest + SOURCE_FORMATS[source]
    )

    if destination.exists():
        if destination.read_bytes() != content:
            raise RuntimeError("Existing raw response failed verification.")
    else:
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=directory,
                prefix=".pending-",
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())

            os.replace(temporary_path, destination)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    return {
        "path": destination.relative_to(PROJECT_ROOT).as_posix(),
        "sha256": digest,
        "size_bytes": len(content),
    }