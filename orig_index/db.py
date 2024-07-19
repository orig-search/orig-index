import local_conf

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Column,
    create_engine,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class Archive(Base):
    __tablename__ = "archive"

    hash = Column(String(64), primary_key=True)
    url = Column(String(256), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    files = relationship("FileInArchive", back_populates="archive")

    # Both of these should be pre-normalized
    canonical_name = Column(String(256), index=True)
    version = Column(String(256))

    @property
    def filename(self):
        return self.url.split("/")[-1]

    def __repr__(self):
        if self.canonical_name:
            return f"Archive({self.filename}, canonical_name={self.canonical_name})"
        else:
            return f"Archive({self.filename})"


class File(Base):
    __tablename__ = "file"

    hash = Column(String(64), primary_key=True)
    normalized_hash = Column(
        String(64), ForeignKey("normalized_file.hash"), nullable=False, index=True
    )
    normalized = relationship("NormalizedFile", back_populates="denorm_files")
    # TODO oldest/canonical archive
    archives = relationship("FileInArchive", back_populates="file")


class FileInArchive(Base):
    __tablename__ = "file_in_archive"

    id = Column(Integer, primary_key=True)  # TODO actually do not want

    archive_hash = Column(
        String(64), ForeignKey("archive.hash"), nullable=False, index=True
    )
    file_hash = Column(String(64), ForeignKey("file.hash"), nullable=False, index=True)

    archive = relationship("Archive")
    file = relationship("File")
    # A given hash can exist more than once in an archive -- this just records an arbitrary one.
    sample_name = Column(String(256))
    vendor_level = Column(Integer)
    # TODO perms, owner, etc
    # normalized_file = relationship("FileInArchive", back_populates="files")

    def __repr__(self):
        return f"FileInArchive(archive_hash={self.archive_hash!r}, file_hash={self.file_hash!r})"


class NormalizedFile(Base):
    """
    A normalized file is like a regular file, but many different regular files can normalize to the same.
    """

    __tablename__ = "normalized_file"

    hash = Column(String(64), primary_key=True)
    snippets = relationship("SnippetInNormalizedFile", back_populates="normalized_file")

    denorm_files = relationship("File", back_populates="normalized")


class SnippetInNormalizedFile(Base):
    __tablename__ = "snippet_in_normalized_file"

    id = Column(Integer, primary_key=True)  # TODO actually do not want
    normalized_file_hash = Column(
        String(64),
        ForeignKey("normalized_file.hash"),
        nullable=False,
        index=True,
    )
    snippet_hash = Column(
        String(64), ForeignKey("snippet.hash"), nullable=False, index=True
    )
    # TODO sequence (or just start line)

    normalized_file = relationship("NormalizedFile")
    snippet = relationship("Snippet", back_populates="normalized_files")


class Snippet(Base):
    """
    A snippet is some normalized lines -- close to syntactically valid, but not guaranteed.

    This might be a ~toplevel function, or some lines in between ~toplevel functions.
    """

    __tablename__ = "snippet"
    hash = Column(String(64), primary_key=True)

    text = Column(Text)
    # This should probably be denormalized further, with the model or other params as another field.
    embedding = Column(Vector(768))
    normalized_files = relationship("SnippetInNormalizedFile", back_populates="snippet")

    __tableargs__ = (
        Index(
            "ix_snippet",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_l2_ops"},
        ),
    )


# TODO embedding index

engine = create_engine(
    local_conf.CONNECTION_STRING,
    # echo=True,
    future=True,
)
Session = sessionmaker(engine)
