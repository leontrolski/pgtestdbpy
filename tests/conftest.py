from typing import Iterator

import pgtestdbpy
import pytest


def migrate1(conn: pgtestdbpy.Conn) -> None:
    conn.execute("CREATE TABLE foo (a INT)")


migrator1 = pgtestdbpy.Migrator("migrator1", migrate1)
migrators = [migrator1]


@pytest.fixture(scope="session")
def admin_conn() -> Iterator[pgtestdbpy.Conn]:
    with pgtestdbpy.initdb() as _admin_conn:
        with pgtestdbpy.build_templates(_admin_conn, migrators):
            yield _admin_conn


@pytest.fixture()
def conn(admin_conn: pgtestdbpy.Conn) -> Iterator[pgtestdbpy.Conn]:
    with pgtestdbpy.clone(admin_conn, migrator1) as conn_:
        yield conn_
