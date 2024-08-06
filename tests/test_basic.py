from io import BytesIO

from fastapi.testclient import TestClient
from orig_index.web import APP


def test_lookup():
    tc = TestClient(APP)

    resp = tc.post(
        "/import/project-url/",
        params={
            "project": "six",
            "url": "https://files.pythonhosted.org/packages/71/39/171f1c67cd00715f190ba0b100d606d440a28c93c7714febeca8b79af85e/six-1.16.0.tar.gz",
        },
    )
    assert resp.status_code == 200

    resp = tc.post(
        "/import/project-url/",
        params={
            "project": "six",
            "url": "https://files.pythonhosted.org/packages/6b/34/415834bfdafca3c5f451532e8a8d9ba89a21c9743a0c59fbd0205c7f9426/six-1.15.0.tar.gz",
        },
    )
    assert resp.status_code == 200

    resp = tc.post(
        "/import/project-url/",
        params={
            "project": "pipenv",
            "url": "https://files.pythonhosted.org/packages/d1/67/c29cb9081e5648b754b7ec95482e348b4d616681a3f0ee402ca082b9be02/pipenv-2024.0.1.tar.gz",
        },
    )
    assert resp.status_code == 200

    resp = tc.get(
        "/normalized/hash/0492b6ef10d7b9e3feba7d273d3300b36ab9272cf534f93d133a51638e504f73",
    )
    assert resp.status_code == 200
    assert "six-1.15.0.tar.gz" in {a["filename"] for a in resp.json()["archives"]}

    resp = tc.get(
        "/file/hash/53867fcafe77e16e423728d8f62f15d4e5d8d928c09f2f32d8be6f0cb8614e13",
        follow_redirects=True,
    )
    # resp.url should be /normalized/hash/... as above
    assert resp.status_code == 200

    obj = resp.json()
    assert obj["archives"] == [
        {
            "hash": "9bd1ccbcba05a60e5a5283649cb745ed7fbe5c493d8fbd3ea9a89deb6eee62fb",
            "filename": "pipenv-2.1.80.tar.gz",
        },
        {
            "hash": "x",
            "filename": "six-1.15.0-py2.py3-none-any.whl",
        },
    ]

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
