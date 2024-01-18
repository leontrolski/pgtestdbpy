# pgtestdbpy

_Python clone of [pgtestdb](https://github.com/peterldowns/pgtestdb)._

```bash
pip install pgtestdbpy
```

In summary, it's a couple of helper functions that allow you to quickly clone Postgres databases that you've applied migrations to. In a small number of milliseconds, each test (including tests running in parallel) gets a fresh db with empty tables, all the sequences reset, etc.

In developing this on my mac, for reasons I don't quite understand, running with Postgres in docker (via [colima](https://github.com/abiosoft/colima)) was substantially quicker that running Postgres natively. So I agree with Peter's advice, just copy [this file](docker-compose.yml) and `docker compose up -d db`.

There are two context managers that can be used in conjunction or independently depending on test setup:

- `pgtestdbpy.templates(config, migrators)`:
    - Creates a new user and database for a migrator.
    - Runs the set of migrations.
    - Marks the database as a `TEMPLATE DATABASE` so that it can be cheaply cloned.
    - Yields.
    - Drops the template database and the user.
- `pgtestdbpy.clone(config, migrator)`:
    - Does a `CREATE DATABASE WITH TEMPLATE` (from a template database made above) giving it a unique random name.
    - Yields a Postgres url for it.
    - Drops the database.

Example `conftest.py` usage below, in theory (I haven't tested this) it should be easy to run tests in parallel using the `conn` fixture - each with a separate database instance - and [pytest-xdist](https://github.com/pytest-dev/pytest-xdist) or equivalent. In this example we just

```python
from typing import Iterator
import pgtestdbpy
import psycopg
import pytest

def migrate(url: str) -> None:
    with psycopg.connect(url) as conn:
        conn.execute("CREATE TABLE foo (a INT)")

migrator = pgtestdbpy.Migrator(migrate)
config = pgtestdbpy.Config()

@pytest.fixture(scope="session")
def db() -> Iterator[None]:
    with pgtestdbpy.templates(config, migrator):
        yield

@pytest.fixture()
def conn(db) -> Iterator[pgtestdbpy.PsycoConn]:
    with pgtestdbpy.clone(config, migrator) as url:
        with psycopg.connect(url) as _conn:
            yield _conn
```
