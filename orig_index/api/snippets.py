from fastapi.exceptions import HTTPException
from sqlalchemy import func, select

from ..db import (
    Archive,
    File,
    FileInArchive,
    NormalizedFile,
    Session,
    Snippet,
    SnippetInNormalizedFile,
)


def api_snippet_detail(hash):
    """
    Returns:
    - the snippet text
    - the first-seen archive
    - number of archives grouped by project
    """
    ret = {
        "hash": hash,
    }
    with Session() as sess:
        snip = sess.get(Snippet, hash)
        if not snip:
            raise HTTPException(404)
        ret["text"] = snip.text
        ret["archives"] = []
        for cn, h, ts, c in sess.execute(
            select(
                Archive.canonical_name,
                func.min(Archive.hash),
                func.min(Archive.timestamp).label("ts"),
                func.count(),
            )
            .join(File.normalized)
            .join(File.archives)
            .join(NormalizedFile.snippets)
            .join(FileInArchive.archive)
            .join(SnippetInNormalizedFile.snippet)
            .where(Snippet.hash == hash)
            .group_by(Archive.canonical_name)
            .order_by("ts")
        ):
            ret["archives"].append(
                {
                    "hash": h,
                    "purl": f"pkg:pypi/{cn}",
                    "earliest_timestamp": ts,
                    "count": c,
                }
            )

    return ret


def api_snippet_similar(hash, n=10):
    """
    Returns:
    - the snippet text
    """
