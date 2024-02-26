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
    with pgtestdbpy.template(config, migrator):
        yield


@pytest.fixture()
def conn(db) -> Iterator[pgtestdbpy.PsycoConn]:
    with pgtestdbpy.clone(config, migrator) as url:
        with psycopg.connect(url) as _conn:
            yield _conn
