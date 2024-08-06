import html
import logging
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile
from fastapi.exceptions import HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2_fragments.fastapi import Jinja2Blocks
from packaging.utils import canonicalize_name
from pypi_simple import ACCEPT_JSON_ONLY, PyPISimple

from .api.archive import api_explore_files_in_archive
from .api.normalized import api_normalized_detail, api_normalized_partial
from .api.snippets import api_snippet_detail

from .db import File, Session, Snippet
from .importer import import_one_local_file, import_url

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logging.getLogger("urllib3.connectionpool").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)

templates = Jinja2Blocks(directory="templates")


class App(FastAPI):
    """Docstring for public class."""

    def __init__(self):
        """Docstring for public method."""
        super(App, self).__init__()
        self.default_name = "orig_web"


APP = App()

APP.mount("/static", StaticFiles(directory="static"), name="static")


@APP.get("/")
async def index(request: Request) -> str:
    return templates.TemplateResponse("index.html", {"request": request})


@APP.get("/api/archive/hash/{hash}")
def archive_hash(hash: str):
    """
    Intended to power an inspector-like gui based on archive hash
    """
    return api_explore_files_in_archive(hash)


@APP.get("/api/normalized/hash/{hash}", response_class=HTMLResponse)
def normalized_detail(hash: str, request: Request):
    """
    Serves the text of the snippets, and mentions what the "oldest" archive
    containing this normalized file is.

    Calculating hash-matches of snippets or embedding-similarity of matches is a
    lot more expensive, and should lazy-load from other endpoints.
    """
    results = api_normalized_detail(hash)
    return templates.TemplateResponse(
        "index.html", {"request": request, "results": results}, block_name="results"
    )


@APP.get("/api/normalized/partial/{hash}", response_class=HTMLResponse)
def normalized_partial(hash: str, request: Request):
    """
    Search for hashes of snippets of this normalized file, assuming that the
    snippets are unmodified.
    """
    results = api_normalized_detail(hash)
    partial = api_normalized_partial(hash)
    snippet_table = "<table border='1'>\n"
    snippet_table += "<tr><th>Source</th>"

    for col in partial["found"]:
        snippet_table += f"<th><a href='{request.url_for('normalized_partial', hash=col['hash'])}' title='{col['hash']}'>{col['hash'][:4]}...</a></th>"

    snippet_table += "</tr>\n"
    for i, snip in enumerate(results["snippets"]):
        snippet_table += "<tr>"
        snippet_table += (
            "<td><pre style='white-space: pre-wrap'>"
            + html.escape(snip["text"])
            + "</pre></td>"
        )
        for col in partial["found"]:
            snippet_table += "<td>" + ("X" if i in col["incl"] else "") + "</td>"
        snippet_table += "</tr>\n"
    snippet_table += "</table>"

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "results": results, "snippet_table": snippet_table},
        block_name="results",
    )


@APP.get("/api/snippet-detail/hash/{hash}")
def snippet_detail(hash: str):
    """
    Intended to power a drill-down page at some point.
    """
    return api_snippet_detail(hash)


@APP.post("/import/project-url/")
def import_project_url(project: str, url: str, request: Request):
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
            return RedirectResponse(
                request.url_for(
                    "archive_hash", hash=distribution_package.digests["sha256"]
                ),
                status_code=303,
            )
    else:
        raise HTTPException(404)


@APP.get("/file/hash/{hash}")
def file_hash(hash: str, request: Request):
    with Session() as session:
        f = session.get(File, hash)
        if not f:
            raise HTTPException(404)

        return RedirectResponse(
            request.url_for("normalized_detail", hash=f.normalized_hash),
            status_code=303,
        )


@APP.get("/snippet/hash/{hash}")
def sinppet_hash(hash: str):
    with Session() as session:
        s = session.get(Snippet, hash)
        if not s:
            raise HTTPException(404)
        return {
            "text": s.text,
            "norm_count": len(s.normalized_files),
            "norm_files": [x.normalized_file_hash for x in s.normalized_files],
        }


@APP.post("/identify/file/")
async def identify_file(file: UploadFile, request: Request):
    local_file = Path(file.filename)

    with Session() as session:
        imported = import_one_local_file(
            fp=None,
            rel=local_file,
            session=session,
            file=file.file,
        )
        session.commit()

        return RedirectResponse(
            request.url_for("normalized_detail", hash=imported.normalized_hash),
            status_code=303,
        )
