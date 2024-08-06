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

        ret = {"found": [], "excluded": None}

        while snippet_hashes_set:
            # TODO break tie better
            (k, v) = max(
                snippets_by_norm.items(), key=lambda i: len(i[1] & snippet_hashes_set)
            )
            # The remaining `snippet_hashes_set` are only sourced from the
            # excluded normalized files, stop the loop.
            if not v & snippet_hashes_set:
                break

            snippet_hashes_set.difference_update(v)
            # Most matching snippets comes first
            ret["found"].append(
                {
                    "hash": k,
                    # TODO requires db change and migration or reindex
                    "oldest_archive": "TODO",
                    # TODO .index is linear
                    "incl": sorted([snippet_hashes.index(i) for i in v]),
                }
            )

        if snippet_hashes_set:
            ret["excluded"] = sorted(
                [snippet_hashes.index(i) for i in snippet_hashes_set]
            )

        return ret
