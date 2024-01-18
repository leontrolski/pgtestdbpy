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
