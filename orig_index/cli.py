import datetime
import hashlib
from pathlib import Path
from typing import Set

import click
import moreorless.click
from packaging.utils import canonicalize_name
from packaging.version import Version
from pypi_simple import ACCEPT_JSON_ONLY, DistributionPackage, PyPISimple
from sqlalchemy import text

from .db import Base, engine, NormalizedFile, Session, Snippet

from .importer import have_hash, import_archive, import_one_local_file, import_url
from .similarity import (
    find_archives_containing_file,
    find_archives_containing_normalized_file,
    find_archives_containing_similar_snippet,
)


@click.group()
def main():
    pass


@main.command()
@click.option("--clear", is_flag=True)
def createdb(clear: bool) -> None:
    if clear:
        Base.metadata.drop_all(engine)
    with Session() as session:
        session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        session.commit()
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


def _unpack_range(s: str) -> Set[int]:
    rv: Set[int] = set()
    for x in s.split(","):
        if "-" in x:
            a, b = map(int, x.split("-", 1))
            rv.update(range(a, b + 1))
        else:
            rv.add(int(x))
    return rv


@main.command()
@click.option("--shard", default="0-99")
@click.option("--of-shards", default="100")
@click.argument("project")
def import_project(project: str, shard: str, of_shards: str) -> None:
    shards = _unpack_range(shard)
    total_shards = int(of_shards)
    if total_shards != len(shards):
        print("Importing %.1f%% of project" % (len(shards) * 100.0 / total_shards,))

    # TODO this could use cachecontrol session
    ps = PyPISimple(accept=ACCEPT_JSON_ONLY)
    cn = canonicalize_name(project)
    pp = ps.get_project_page(cn)
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

        if (
            int.from_bytes(hashlib.sha256(distribution_package.url.encode()).digest())
            % total_shards
        ) not in shards:
            print("omit", distribution_package.url)
            continue

        import_url(
            hash=distribution_package.digests["sha256"],
            url=distribution_package.url,
            date=distribution_package.upload_time,
            project=cn,
            version=distribution_package.version,
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
        print(
            import_one_local_file(
                Path(local_file), Path(local_file), session
            ).normalized.hash
        )
        session.commit()


@main.group()
def lookup():
    pass


@lookup.command()
@click.argument("local_file")
def local_file(local_file: str) -> None:
    with Session() as session:
        imported = import_one_local_file(Path(local_file), Path(local_file), session)
        session.commit()

        print("hash:", imported.hash)
        print("normalized:", imported.normalized.hash)

        found = False
        for (m,) in find_archives_containing_file(imported.hash, session).all():
            print(m.sample_name, "in", m.archive.filename, m.vendor_level)
            found = True

        if not found:
            print("No exact matches, checking near matches...")
            for (m,) in find_archives_containing_normalized_file(
                imported.normalized.hash, session
            ).all():
                print(m.sample_name, "in", m.archive.filename, m.vendor_level)
            # find_
            for snippet in imported.normalized.snippets:
                print(repr(snippet.snippet.text))
                for (
                    m,
                    distance,
                    norm_snippet,
                ) in find_archives_containing_similar_snippet(
                    snippet.snippet, session
                ).all():
                    print(
                        m.sample_name,
                        "in",
                        m.archive.filename,
                        m.vendor_level,
                        distance,
                    )  # , norm_snippet.snippet.text)
                    moreorless.click.echo_color_unified_diff(
                        snippet.snippet.text, norm_snippet.snippet.text, ""
                    )
                print("----")


@lookup.command()
@click.argument("hash")
def normalized_hash(hash: str) -> None:
    with Session() as session:
        normalized_file = session.get(NormalizedFile, hash)
        if normalized_file is None:
            print("Not yet available")
            return
        for s in normalized_file.snippets:
            print(s.snippet.hash)


@lookup.command()
@click.argument("hash")
def snippet_hash(hash: str) -> None:
    with Session() as session:
        snippet = session.get(Snippet, hash)
        for f in snippet.normalized_files:
            print(f.normalized_file_hash, f.denorm_files)


if __name__ == "__main__":
    main()
