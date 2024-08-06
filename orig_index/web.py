import logging
import os
from pathlib import Path

import moreorless
from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
from packaging.utils import canonicalize_name
from pypi_simple import ACCEPT_JSON_ONLY, PyPISimple
from sqlalchemy import select

from .db import Base, File, NormalizedFile, Session, Snippet, SnippetInNormalizedFile
from .importer import have_hash, import_archive, import_one_local_file, import_url
from .similarity import (
    find_archives_containing_file,
    find_archives_containing_normalized_file,
    find_archives_containing_similar_snippet,
)

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)


class App(FastAPI):
    """Docstring for public class."""

    def __init__(self):
        """Docstring for public method."""
        super(App, self).__init__()
        self.default_name = "orig_web"


APP = App()


@APP.get("/")
async def root() -> str:
    return "Visit /docs"


@APP.post("/import/project-url/")
def import_project_url(project: str, url: str):
    """
    Indexes one known url from the given project.

    This is primarily intended for testing, as these would be indexed by some
    background process in due course in a production environment.

    The url must correspond to a DistributionPackage in this project.
    """

    ps = PyPISimple(accept=ACCEPT_JSON_ONLY)
    cn = canonicalize_name(project)
    pp = ps.get_project_page(cn)
    for distribution_package in pp.packages:
        if distribution_package.url == url:
            if distribution_package.package_type not in ("sdist", "wheel"):
                raise HTTPException(500)

            upload_time = distribution_package.upload_time
            assert upload_time is not None
            import_url(
                hash=distribution_package.digests["sha256"],
                url=distribution_package.url,
                date=upload_time,
                project=cn,
                version=distribution_package.version,
            )
            break
    else:
        raise HTTPException(404)


@APP.get("/file/hash/{hash}")
def file_hash(hash: str, request: Request):
    with Session() as session:
        f = session.get(File, hash)
        if not f:
            raise HTTPException(404)

        return RedirectResponse(
            request.url_for("normalized_hash", hash=f.normalized_hash)
        )


@APP.get("/normalized/hash/{hash}")
def normalized_hash(hash: str):
    """
    Finds archives that definitively contain an equivalent file.

    TODO: could use an html renderer as well, this is all pretty quick and is
    enough to display the source code while we wait for much slower near-matches
    calls.
    """
    with Session() as session:
        f = session.get(NormalizedFile, hash)
        if not f:
            raise HTTPException(404)
        return {
            "archives": [
                {"hash": x.archive.hash, "filename": x.archive.filename}
                for (x,) in find_archives_containing_normalized_file(hash, session)
            ],
            "snippets": [
                {"hash": x.hash, "text": x.text}
                for (x,) in session.execute(
                    select(Snippet)
                    .join(NormalizedFile.snippets)
                    .join(SnippetInNormalizedFile.snippet)
                    .where(NormalizedFile.hash == hash)
                    .order_by(SnippetInNormalizedFile.sequence)
                ).all()
            ],
        }


@APP.get("/snippet/hash/{hash}")
def sinppet_hash(hash: str):
    with Session() as session:
        s = session.get(Snippet, hash)
        if not s:
            raise HTTPException(404)
        return {
            "text": s.text,
            "norm_count": len(s.normalized_files),
            "norm_files": [
                x.normalized_file_hash for x in s.normalized_files
            ],

        }


@APP.post("/identify/file/")
async def identify_file(file: UploadFile, request: Request):
    local_file = Path(file.filename)
    results = {}

    with Session() as session:
        imported = import_one_local_file(
            fp=None,
            rel=local_file,
            session=session,
            file=file.file,
        )
        session.commit()

        return RedirectResponse(
            request.url_for("normalized_hash", hash=imported.normalized_hash)
        )


"""
        results["hash"] = imported.hash
        results["normalized_hash"] = imported.normalized.hash
        results["exact_matches"] = []
        results["normalized_matches"] = []
        results["near_matches"] = []

        exact_matches = results["exact_matches"]
        for (m,) in find_archives_containing_file(imported.hash, session).all():
            exact_matches.append(
                {
                    "sample_name": m.sample_name,
                    "archive": m.archive.filename,
                    "vendor_level": m.vendor_level,
                }
            )

        if not exact_matches:
            normalized_matches = results["normalized_matches"]
            print("No exact matches, checking normalized matches...")
            for (m,) in find_archives_containing_normalized_file(
                imported.normalized.hash, session
            ).all():
                normalized_matches.append(
                    {
                        "sample_name": m.sample_name,
                        "archive": m.archive.filename,
                        "vendor_level": m.vendor_level,
                    }
                )

        if not normalized_matches:
            near_matches = results["near_matches"]
            print("No normalized matches, checking near matches...")
            for snippet in imported.normalized.snippets:
                for (
                    m,
                    distance,
                    norm_snippet,
                ) in find_archives_containing_similar_snippet(
                    snippet.snippet, session
                ).all():
                    near_matches.append(
                        {
                            "sample_name": m.sample_name,
                            "archive": m.archive.filename,
                            "vendor_level": m.vendor_level,
                            "distance": distance,
                            "diff": moreorless.unified_diff(
                                snippet.snippet.text,
                                norm_snippet.snippet.text,
                                "example.py",
                            ),
                        }
                    )
    os.remove(local_file)
    return results
"""
