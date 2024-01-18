import pgtestdbpy

from tests.conftest import config


def test_insert_and_select(conn: pgtestdbpy.PsycoConn) -> None:
    conn.execute("INSERT INTO foo (a) VALUES (1), (2), (3)")
    rows = conn.execute("SELECT * FROM foo")
    assert list(rows) == [(1,), (2,), (3,)]


def test_timeit(db: None) -> None:
    for _ in range(60):
        dummy_migrator = pgtestdbpy.Migrator(lambda _: None)
        # Approx 15ms per clone
        with pgtestdbpy.clone(config, dummy_migrator) as url:
            ...
