import ast
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

import requests
from sqlalchemy.dialects.postgresql import insert

from .db import (
    Archive,
    File,
    FileInArchive,
    NormalizedFile,
    Session,
    Snippet,
    SnippetInNormalizedFile,
)
from .norm import normalize
from .split import segment


def have_hash(sha256: str) -> bool:
    """
    Assume that once added, things are never deleted.

    If this archive hash exists already, then we don't need to import it again.

    Revisit if there are ever multiple ways to compute normalized code, or embeddings.
    """
    with Session() as session:
        t = session.get(Archive, sha256)
        return bool(t)


def import_url(hash, url, date) -> None:
    if hash is not None and have_hash(hash):
        return

    with tempfile.TemporaryDirectory() as td:
        local_filename = url.split("/")[-1]
        hasher = hashlib.sha256()
        with open(Path(td, local_filename), "wb") as f:
            with requests.get(url, stream=True) as resp:
                for chunk in resp.iter_content(None):
                    f.write(chunk)
                    hasher.update(chunk)

        return import_archive(hasher.hexdigest(), url, date, Path(td, local_filename))


def import_archive(
    hash, url, date, local_file
) -> None:  # TODO maybe return a stats object?
    print(f"[FILE] {hash} from {url}")
    if have_hash(hash):
        print("  -> already have")
        return

    # TODO ignore cleanup errors
    with tempfile.TemporaryDirectory() as td:
        shutil.unpack_archive(local_file, td, format="zip")

        # TODO handle retries here until it succeeds!
        with Session() as session:
            import_local_dir(
                archive_hash=hash,
                archive_url=url,
                archive_date=date,
                local_dir=td,
                session=session,
            )
            session.commit()


def import_local_dir(archive_hash, archive_url, archive_date, local_dir, session):
    archive = session.get(Archive, archive_hash)
    if archive is None:
        archive = Archive(hash=archive_hash, url=archive_url, timestamp=archive_date)
        print("  -> create")
        session.add(archive)

    for dirpath, dirnames, filenames in os.walk(local_dir):
        dirnames[:] = [d for d in dirnames if d not in (".venv",)]
        for f in filenames:
            # TODO consider pyi?
            if f.endswith(".py"):
                fp = Path(dirpath, f)
                orm_file = import_one_local_file(fp, session)
                if orm_file:
                    orm_file_in_archive = FileInArchive(archive=archive, file=orm_file)
                    session.add(orm_file_in_archive)


def import_one_local_file(fp: Path, session) -> File:
    data = fp.read_bytes()
    h = hashlib.sha256(data).hexdigest()
    orm_file = session.get(File, h)
    if orm_file is None:
        # Step 1: normalize
        mod = normalize(ast.parse(data))
        normalized_bytes = ast.unparse(mod).encode("utf-8")
        nh = hashlib.sha256(normalized_bytes).hexdigest()
        orm_normalized = session.get(NormalizedFile, nh)
        if orm_normalized is not None:
            print("  [NOM]")
        else:
            print("  [SEG]", fp)
            # Step 2: normalized missing too, upsert/collect snippet objects
            segments = list(segment(mod))
            if not segments:
                # An empty or whitespace-only file has no segments, don't bother indexing.
                print("  [WS ONLY]")
                return
            print(segments)
            stmt = (
                insert(Snippet)
                .values(
                    [
                        {
                            "hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                            "text": text,
                        }
                        for a, b, text in segments
                    ]
                )
                .on_conflict_do_nothing()
                .returning(Snippet)
            )
            result = session.execute(stmt)
            result_all = result.all()
            print("RES", result_all)
            new_snippet_in_normalized = [
                SnippetInNormalizedFile(
                    normalized_file_hash=nh,
                    snippet_hash=r.hash,
                )
                for r in result_all[0]
            ]
            session.add(*new_snippet_in_normalized)

            orm_normalized = NormalizedFile(hash=nh, snippets=new_snippet_in_normalized)
            session.add(orm_normalized)

        # TODO needs some other arg to make normalized->normalized_hash magic happen
        orm_file = File(hash=h, normalized=orm_normalized)
        session.add(orm_file)
    return orm_file
