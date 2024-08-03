from io import BytesIO

import orig_index.importer

from fastapi.testclient import TestClient
from orig_index.overly_simple_embedding import SimpleModel
from orig_index.web import APP


def test_lookup():
    # TODO yield-fixture, proper monkeypatch
    def get_model():
        return SimpleModel(512)

    orig_index.importer.get_model = get_model

    tc = TestClient(APP)

    # This is the most recent version as of when I'm writing this test in 2024
    resp = tc.post(
        "/import/project-url/",
        params={
            "project": "six",
            "url": "https://files.pythonhosted.org/packages/71/39/171f1c67cd00715f190ba0b100d606d440a28c93c7714febeca8b79af85e/six-1.16.0.tar.gz",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    # This version is from 2017, but after urllib3's release
    resp = tc.post(
        "/import/project-url/",
        params={
            "project": "six",
            "url": "https://files.pythonhosted.org/packages/16/d8/bc6316cf98419719bd59c91742194c111b6f2e85abac88e496adefaf7afe/six-1.11.0.tar.gz",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    resp = tc.post(
        "/import/project-url/",
        params={
            "project": "urllib3",
            "url": "https://files.pythonhosted.org/packages/96/d9/40e4e515d3e17ed0adbbde1078e8518f8c4e3628496b56eb8f026a02b9e4/urllib3-1.21.1.tar.gz",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    resp = tc.get(
        "/normalized/hash/59c1a2c0e1325d2b18c77960cbe688bd54232669451f27abbce2666ec129a9ba",
    )
    assert resp.status_code == 200
    obj = resp.json()
    assert "six-1.16.0.tar.gz" in {a["filename"] for a in obj["archives"]}

    # assert obj["archives"] == [
    #    {
    #        "hash": "9bd1ccbcba05a60e5a5283649cb745ed7fbe5c493d8fbd3ea9a89deb6eee62fb",
    #        "filename": "pipenv-2.1.80.tar.gz",
    #    },
    #    {
    #        "hash": "x",
    #        "filename": "six-1.15.0-py2.py3-none-any.whl",
    #    },
    # ]

    # TODO find the non-normalized hash for that file
    # resp = tc.get(
    #     "/file/hash/...",
    #     follow_redirects=True,
    # )
    # # resp.url should be /normalized/hash/... as above
    # assert resp.status_code == 200

    resp = tc.get(
        "/snippet/hash/a4253c1c870587f288332f4bc445d275dfb6849d45b8fb78ed12d2fd8ea96603"
    )
    assert resp.status_code == 200
    assert (
        resp.json()["text"]
        == "if sys.version_info[:2] < (3, 3):\n    _print = print_\n"
    )

    # There are some small intentional changes here...
    fo = BytesIO(
        b"if sys.version_info[:2] < (3, 3):\n    '''Some docstring'''\n    _print=print_"
    )
    resp = tc.post(
        "/identify/file/",
        files={"file": ("filename", fo, "text/plain")},
        follow_redirects=True,
    )
    # /normalized/hash/26aa648ce5edc57b15c49ac224b9ea6357450e5b120f496a73a4879240d606c2
    assert resp.status_code == 200
    assert resp.json()["snippets"] == [
        {
            "hash": "26aa648ce5edc57b15c49ac224b9ea6357450e5b120f496a73a4879240d606c2",
            "text": "if sys.version_info[:2] < (3, 3):\n    _print = print_",
        }
    ]
