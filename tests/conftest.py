import sys

import orig_index.db
import orig_index.importer
import orig_index.web
import pytest
from orig_index.db import _createdb, recreate_engine
from testcontainers.postgres import PostgresContainer

pgvector = PostgresContainer("ankane/pgvector:latest")


@pytest.fixture(scope="module", autouse=True)
def setup_testcontainer(request):
    pgvector.start()
    request.addfinalizer(pgvector.stop)

    class FakeModule:
        CONNECTION_STRING = pgvector.get_connection_url(driver="psycopg")

    sys.modules["local_conf"] = FakeModule
    recreate_engine()

    # From-imports need to be updated, this is going to get tedious
    orig_index.web.Session = orig_index.db.Session
    orig_index.importer.Session = orig_index.db.Session


@pytest.fixture(scope="function", autouse=True)
def withpg():
    _createdb(clear=True)
