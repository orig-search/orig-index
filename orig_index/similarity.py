from sqlalchemy import select

from .db import (
    Archive,
    File,
    FileInArchive,
    NormalizedFile,
    Session,
    Snippet,
    SnippetInNormalizedFile,
)


def find_archives_containing_file(hash: str, session: Session):
    return session.execute(
        select(FileInArchive)
        .join(Archive.files)
        .where(FileInArchive.file_hash == hash)
        .order_by(FileInArchive.vendor_level)
    )


def find_archives_containing_normalized_file(hash: str, session: Session):
    return session.execute(
        select(FileInArchive)
        .join(File.archives)
        .where(File.normalized_hash == hash)
        .order_by(FileInArchive.vendor_level)
    )
