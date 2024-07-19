import ast
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

import requests
from sqlalchemy import select
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

MODEL = None

VENDOR_DIR_NAMES = {"vendor", "_vendor", "vendored", "_vendored"}


def get_model():
    global MODEL
    if MODEL is None:
        from sentence_transformers import SentenceTransformer

        MODEL = SentenceTransformer(
            os.getenv(
                "MODEL_NAME",
                "flax-sentence-embeddings/st-codesearch-distilroberta-base",
            )
        )
    return MODEL


def have_hash(sha256: str) -> bool:
    """
    Assume that once added, things are never deleted.

    If this archive hash exists already, then we don't need to import it again.

    Revisit if there are ever multiple ways to compute normalized code, or embeddings.
    """
    with Session() as session:
        t = session.get(Archive, sha256)
        return bool(t)


def import_url(hash, url, date, project, version) -> None:
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

        return import_archive(
            hasher.hexdigest(), url, date, Path(td, local_filename), project, version
        )


def import_archive(
    hash, url, date, local_file, project, version
) -> None:  # TODO maybe return a stats object?
    print(f"[FILE] {hash} from {url}")
    if have_hash(hash):
        print("  -> already have")
        return

    # TODO ignore cleanup errors
    with tempfile.TemporaryDirectory() as td:
        format = "zip" if local_file.suffix in (".zip", ".whl") else "tar"
        shutil.unpack_archive(local_file, td, format=format)

        # TODO handle retries here until it succeeds!
        with Session() as session:
            import_local_dir(
                archive_hash=hash,
                archive_url=url,
                archive_date=date,
                local_dir=td,
                session=session,
                project=project,
                version=version,
            )
            session.commit()


def import_local_dir(
    archive_hash: str,
    archive_url: str,
    archive_date,
    local_dir,
    session,
    project: str,
    version: str,
):
    archive = session.get(Archive, archive_hash)
    if archive is None:
        archive = Archive(
            hash=archive_hash,
            url=archive_url,
            timestamp=archive_date,
            canonical_name=project,
            version=version,
        )
        print("  -> create")
        session.add(archive)

    for dirpath, dirnames, filenames in os.walk(local_dir):
        dirnames[:] = [d for d in dirnames if d not in (".venv",)]
        for f in filenames:
            # TODO consider pyi?
            if f.endswith(".py"):
                fp = Path(dirpath, f)
                relative_name = fp.relative_to(local_dir)
                orm_file = import_one_local_file(fp, fp.relative_to(local_dir), session)
                vendor_level = sum(
                    1 for part in relative_name.parts if part in VENDOR_DIR_NAMES
                )
                if orm_file:
                    orm_file_in_archive = FileInArchive(
                        archive=archive,
                        file=orm_file,
                        sample_name=relative_name.as_posix(),
                        vendor_level=vendor_level,
                    )
                    session.add(orm_file_in_archive)


def import_one_local_file(fp: Path, rel: Path, session) -> File:
    data = fp.read_bytes()
    h = hashlib.sha256(data).hexdigest()
    orm_file = session.get(File, h)
    if orm_file is not None:
        print("  [HIT ]", rel)
    else:
        # Step 1: normalize
        mod = normalize(ast.parse(data))
        normalized_bytes = ast.unparse(mod).encode("utf-8")
        nh = hashlib.sha256(normalized_bytes).hexdigest()
        orm_normalized = session.get(NormalizedFile, nh)
        if orm_normalized is not None:
            print("  [HIT2]", rel)
        else:
            # Step 2: normalized missing too, upsert/collect snippet objects
            segments = list(segment(mod))
            if not segments:
                # An empty or whitespace-only file has no segments, don't bother indexing.
                print("  [    ]", rel)
                return
            print("  [----]", rel)
            values = [
                {
                    "hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "text": text,
                }
                for a, b, text in segments
            ]
            stmt = (
                insert(Snippet)
                .values(values)
                .on_conflict_do_nothing()
                .returning(Snippet)
            )
            ret = session.execute(stmt)
            model = get_model()
            for (x,) in ret:
                x.embedding = model.encode(x.text)

            hashes = [v["hash"] for v in values]
            # result = session.execute(select(Snippet).where(Snippet.hash.in_(hashes)))
            # result_all = {r[0].hash: r[0] for r in result.all()}

            new_snippet_in_normalized = [
                SnippetInNormalizedFile(
                    normalized_file_hash=nh,
                    snippet_hash=h,
                    sequence=i,
                )
                for i, h in enumerate(hashes)
            ]
            for s in new_snippet_in_normalized:
                session.add(s)

            orm_normalized = NormalizedFile(hash=nh, snippets=new_snippet_in_normalized)
            session.add(orm_normalized)

        orm_file = File(hash=h, normalized=orm_normalized)
        session.add(orm_file)
    return orm_file
