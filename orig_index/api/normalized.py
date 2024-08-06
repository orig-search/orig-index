from collections import defaultdict

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


def api_normalized_detail(hash):
    """
    Returns:
    - the "oldest" source of this normalized hash
    - the snippet texs in order, and their hashes
    """

    ret = {
        "hash": hash,
        # TODO requires db change and migration or reindex
        "oldest_archive": "TODO",
    }

    with Session() as sess:
        norm = sess.get(NormalizedFile, hash)
        if not norm:
            raise HTTPException(404)
        ret["snippets"] = [
            {"hash": x.hash, "text": x.text}
            for (x,) in sess.execute(
                select(Snippet)
                .join(NormalizedFile.snippets)
                .join(SnippetInNormalizedFile.snippet)
                .where(NormalizedFile.hash == hash)
                .order_by(SnippetInNormalizedFile.sequence)
            )
        ]
        return ret


def api_normalized_partial(hash):
    with Session() as sess:
        norm = sess.get(NormalizedFile, hash)
        snippet_hashes = [
            x
            for (x,) in sess.execute(
                select(Snippet.hash)
                .join(NormalizedFile.snippets)
                .join(SnippetInNormalizedFile.snippet)
                .where(NormalizedFile.hash == hash)
                .order_by(SnippetInNormalizedFile.sequence)
            )
        ]

        snippet_hashes_set = set(snippet_hashes)

        snippets_by_norm = defaultdict(set)
        for norm_hash, snippet_hash in sess.execute(
            select(NormalizedFile.hash, Snippet.hash)
            .join(NormalizedFile.snippets)
            .join(SnippetInNormalizedFile.snippet)
            .where(Snippet.hash.in_(snippet_hashes_set))
            # TODO this could easily exclude multiple
            .where(NormalizedFile.hash != hash)
        ):
            snippets_by_norm[norm_hash].add(snippet_hash)

        ret = []

        while snippet_hashes_set:
            # TODO break tie better
            (k, v) = max(
                snippets_by_norm.items(), key=lambda i: len(i[1] & snippet_hashes_set)
            )
            snippet_hashes_set.difference_update(v)
            ret.append(
                {
                    "hash": k,
                    # TODO requires db change and migration or reindex
                    "oldest_archive": "TODO",
                    # TODO .index is linear
                    "incl": sorted([snippet_hashes.index(i) for i in v]),
                }
            )
        return ret
