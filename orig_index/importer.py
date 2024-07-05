import tempfile

import requests

from .db import get_connection


def have_hash(sha256: str) -> bool:
    """
    Assume that once added, things are never deleted.

    If this archive hash exists already, then we don't need to import it again.

    Revisit if there are ever multiple ways to compute normalized code, or embeddings.
    """
    conn = get_connection()
    return conn.query("select * from archives where hash=%s", (sha256,)).rowcount


def import_url(hash, url, date) -> None:
    if have_hash(hash):
        return

    with tempfile.TemporaryDirectory() as td:
        local_filename = url.split("/")[-1]
        with open(Path(td, local_filename), "wb") as f:
            with requests.get(url, stream=True) as resp:
                for chunk in resp.iter_content(None):
                    f.write(chunk)

        return import_file(hash, url, date, Path(td, local_filename))


def import_file(
    hash, url, date, local_file
) -> None:  # TODO maybe return a stats object?
    if have_hash(hash):
        return

    # TODO ignore cleanup errors
    with tempfile.TemporaryDirectory() as td:
        shutil.unpack_archive(local_file, td)

        # TODO start a transaction here, handle retry, etc?
        import_local_dir(archive_hash=hash, local_dir=td)


def import_local_dir(archive_hash, local_dir):
    for dirpath, dirnames, filenames in os.walk(local_dir):
        dirnames[:] = [d for d in dirnames if d not in (".venv",)]
        for f in filenames:
            # TODO consider pyi?
            if f.endswith(".py"):
                ...
