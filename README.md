# orig-index

# Database

```
docker volume create pgdata
docker run -P --name pgvector -e POSTGRES_PASSWORD=... -v pgdata:/var/lib/postgresql/data -d ankane/pgvector
# default mapping is 0.0.0.0:32768

cat local_conf.py
CONNECTION_STRING = "postgresql+psycopg://postgres:...@localhost:32768/postgres"

export PYTHONPATH=$PWD to find local_conf.py too in addition to make setup
```

# Version Compat

Usage of this library should work back to 3.7, but development (and mypy
compatibility) only on 3.10-3.12.  Linting requires 3.12 for full fidelity.

# Versioning

This library follows [meanver](https://meanver.org/) which basically means
[semver](https://semver.org/) along with a promise to rename when the major
version changes.

# License

orig-index is copyright [Tim Hatch, Amjith Ramanujam](https://github.com/orig-search/), and licensed under
the MIT license.  See the `LICENSE` file for details.
