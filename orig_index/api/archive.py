from fastapi.exceptions import HTTPException

from ..db import Archive, Session


def api_explore_files_in_archive(hash):
    with Session() as sess:
        archive = sess.get(Archive, hash)
        if not archive:
            raise HTTPException(404)

        ret = {
            "url": archive.url,
            "files": [
                {
                    "normalized_hash": fia.file.normalized_hash,
                    "sample_name": fia.sample_name,
                }
                for fia in archive.files
            ],
        }

        return ret
