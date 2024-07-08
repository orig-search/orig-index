import datetime
import hashlib
from pathlib import Path

import click
from packaging.version import Version
from pypi_simple import ACCEPT_JSON_ONLY, DistributionPackage, PyPISimple

from .db import Base, engine, Session

from .importer import have_hash, import_archive, import_one_local_file, import_url


@click.group()
def main():
    pass


@main.command()
@click.option("--clear", is_flag=True)
def createdb(clear: bool) -> None:
    if clear:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def rank(dp: DistributionPackage) -> int:
    if dp.package_type == "sdist":
        return 10
    elif "-py3-none-any" in dp.filename:
        return 5
    elif "-py2.py3-none-any" in dp.filename:
        return 4
    elif "abi3" in dp.filename:
        return 2
    elif "cp312" in dp.filename:
        return 1
    elif dp.package_type != "wheel":
        return -1
    return 0


@main.command()
@click.argument("project")
def import_project(project: str) -> None:
    # TODO this could use cachecontrol session
    ps = PyPISimple(accept=ACCEPT_JSON_ONLY)
    pp = ps.get_project_page(project)
    versions = sorted(
        {dp.version for dp in pp.packages},
        key=Version,
        reverse=True,
    )
    for version in versions:
        distribution_package = max(
            [dp for dp in pp.packages if dp.version == version],
            key=rank,
        )

        # .filename
        # .digests["sha256"]
        # .url
        # .size (only if json-fetched)
        # .upload_time (only if json-fetched)
        # .package_type == "wheel" for now
        if distribution_package.package_type not in ("sdist", "wheel"):
            continue

        import_url(
            hash=distribution_package.digests["sha256"],
            url=distribution_package.url,
            date=distribution_package.upload_time,
        )


@main.command()
@click.argument("url")
def import_a_url(url):
    import_url(
        hash=None, url=url, date=datetime.datetime(3000, 1, 1, tzinfo=datetime.UTC)
    )


@main.command()
# TODO multiple, require it exists
@click.argument("local_file")
def import_local_archive(local_file: str) -> None:
    with open(local_file, "rb") as f:
        h = hashlib.sha256()
        while chunk := f.read(8192):
            h.update(chunk)

    import_archive(
        hash=h.hexdigest(),
        url=local_file,  # TODO could also take an arg, or see if it's on files.pythonhosted.org
        date=datetime.datetime(
            3000, 1, 1, tzinfo=datetime.UTC
        ),  # TODO could also use mtime?
        local_file=local_file,
    )


@main.command()
# TODO multiple, require it exists
@click.argument("local_file")
def import_local_file(local_file: str) -> None:
    with Session() as session:
        print(import_one_local_file(Path(local_file), session).normalized.hash)
        session.commit()


if __name__ == "__main__":
    main()
