import datetime
import hashlib

import click
from pypi_simple import ACCEPT_JSON_ONLY, PyPISimple

from .importer import have_hash, import_file, import_url


@click.group()
def main():
    pass


@main.command()
@click.argument("project")
def import_project(project: str) -> None:
    # TODO this could use cachecontrol session
    ps = PyPISimple(accept=ACCEPT_JSON_ONLY)
    pp = ps.get_project_page(project)
    for distribution_package in pp.packages:
        # .filename
        # .digests["sha256"]
        # .url
        # .size (only if json-fetched)
        # .upload_time (only if json-fetched)
        # .package_type == "wheel" for now
        if distribution_package.package_type != "wheel":
            continue

        import_url(
            hash=distribution_package.digests["sha256"],
            url=distribution_package.url,
            date=distribution_package.upload_time,
        )


@main.command()
# TODO multiple, require it exists
@click.argument("local_file")
def import_local_file(local_file: str) -> None:
    with open(local_file, "rb") as f:
        h = hashlib.sha256()
        while chunk := f.read(8192):
            h.update(chunk)

    import_file(
        hash=h.hexdigest(),
        url=local_file,  # TODO could also take an arg, or see if it's on files.pythonhosted.org
        date=datetime.datetime(
            3000, 1, 1, tzinfo=datetime.UTC
        ),  # TODO could also use mtime?
        local_file=local_file,
    )
