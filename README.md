# orig-index

This is the component responsible for calculating embeddings and similarity of source code.

# Database

```
docker volume create pgdata
docker run -P --name pgvector -e POSTGRES_PASSWORD=... -v pgdata:/var/lib/postgresql/data -d ankane/pgvector
# first available mapping appears to be 0.0.0.0:32768 on linux or :55000 on mac

cat local_conf.py
CONNECTION_STRING = "postgresql+psycopg://postgres:...@localhost:32768/postgres"

export PYTHONPATH=$PWD to find local_conf.py too in addition to make setup
```

# Indexing

If you import a single file at a time, the few seconds up front to load the
model may dominate.  Specifying multiple projects helps with this as they share
one model load.

1. Check archive sha256 to see if it's already imported
2. Check individual file sha256 to see if it's already imported
3. Check a normalized file sha256 to see if an equivalent one is already imported
4. If all else fails, divide the file into "snippets" and index each of those
   (but ones we've seen before don't need embeddings recalculated).

```
# This can use about 4 cores of cpu-based torch (when there are a lot of new
# files), more like 1 core when it's a lot of cache hits.  This imports one
# artifact from each version until it hits a parse error from the py2 days... 
orig import-project requests

# Or if you have cuda, this can use most of a 4GB GTX 1050 Ti and about 5 cores
# to import at roughly 10x the rate of above.  Input archives are about 25Mbps
# of primarily sdists.
cat testdata/sample-projects.txt | xargs -n10 -P8 orig import-project

# If you have multuple machines contributing, you can also specify shards, e.g.
# for a deterministic 1/3 of all urls...
--shard 0-33 --of-shards 100
```

You can change the choice of model with `MODEL_NAME` env var, but that also
requires a change to the `Vector` column in `db.py`, as well as a `orig
createdb --clear` and subsequent reindexing from scratch.

# Querying

Internally this indexes the file first, but then reports a lot more information
than the indexing step does.

1. Exact match ("HIT" during index)
2. Normalized match ("HIT2" during index)
3. Snippet similarity (very verbose)

```
# extract and modify a file out of a known sdist, for example
orig lookup local-file /path/to/file.py
```

# Version Compat

Because this uses `ast` to normalize code, this needs to be run on one
consistent, modern version.  Right now that is 3.12.

# Versioning

This library follows [meanver](https://meanver.org/) which basically means
[semver](https://semver.org/) along with a promise to rename when the major
version changes.

# License

orig-index is copyright [Tim Hatch, Amjith Ramanujam](https://github.com/orig-search/), and licensed under
the MIT license.  See the `LICENSE` file for details.
