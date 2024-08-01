import logging
import os
from pathlib import Path

import moreorless.click
from fastapi import Depends, FastAPI, HTTPException, UploadFile

from .db import Base, engine, NormalizedFile, Session, Snippet
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


@APP.post("/lookup/")
async def lookup(file: UploadFile):
    local_file = Path(file.filename)
    results = {}

    with Session() as session:
        imported = import_one_local_file(Path(local_file), Path(local_file), session)
        session.commit()

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
                            "diff": moreorless.click.echo_color_unified_diff(
                                snippet.snippet.text, norm_snippet.snippet.text, ""
                            ),
                        }
                    )
    os.remove(local_file)
    return results
