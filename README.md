# pgtestdbpy

Python clone of [pgtestdb](https://github.com/peterldowns/pgtestdb) (with further inspiration from [testing.postgresql](https://github.com/tk0miya/testing.postgresql)).

_Not particularly useful as it's much slower for me than advertised in the original library (need to investigate why this is the case - it's 50-100ms per clone on my machine)._

There are two configuration dataclasses:

- `pgtestdbpy.initdb.Config` contains configuration to set up a database (with sane defaults).
- `pgtestdbpy.initdb.Migrator` contains configuration for a set of migrations, most importantly a unique name - `db_name=` for the set of migrations and a function to perform them - `migrate=`.

Then there are three functions that can be used in conjunction or independently depending on test setup:

- `pgtestdbpy.initdb(config)` - context manager that:
    - Calls `initdb` to create a postgres db in a temporary directory.
    - Yields.
    - Stops and tears down the db.
- `pgtestdbpy.build_templates(config, migrators)` - function that for each migrator:
    - Checks for the existence of a test user and a template database. If they don't exist, it:
    - Creates a new user and database.
    - Runs the set of migrations.
    - Marks the database as a `TEMPLATE DATABASE` so that it can be cheaply cloned.
- `pgtestdbpy.clone(config, migrator)` - context manager that:
    - Does a `CREATE DATABASE WITH TEMPLATE` (from a template database made above) giving it a unique random name.
    - Yields a postgres url for it.
    - Drops the database.

Example `conftest.py` usage below, in theory (I haven't tested this) it should be easy to run tests in parallel using the `conn` fixture - each with a separate database instance - and [pytest-xdist](https://github.com/pytest-dev/pytest-xdist) or equivalent.

```python
from typing import Iterator
import pgtestdbpy
import psycopg
import pytest

def migrate(url: str) -> None:
    with psycopg.connect(url) as conn:
        conn.execute("CREATE TABLE foo (a INT)")

migrator = pgtestdbpy.Migrator("migrator", migrate)
migrators = [migrator]

@pytest.fixture(scope="session")
def db() -> Iterator[pgtestdbpy.Config]:
    config = pgtestdbpy.Config()
    with pgtestdbpy.initdb(config):
        pgtestdbpy.build_templates(config, migrators)
        yield config

@pytest.fixture()
def conn(db: pgtestdbpy.Config) -> Iterator[pgtestdbpy.PsycoConn]:
    with pgtestdbpy.clone(db, migrator) as url:
        with psycopg.connect(url) as _conn:
            yield _conn
```

# TODO

- Make it quicker.
- Profile against `DELETE`ing or `TRUNCATE`ing data.
- Publish to `pypi`.
