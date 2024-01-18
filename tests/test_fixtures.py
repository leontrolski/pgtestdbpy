import pgtestdbpy


def test_insert_and_select(conn: pgtestdbpy.PsycoConn) -> None:
    conn.execute("INSERT INTO foo (a) VALUES (1), (2), (3)")
    rows = conn.execute("SELECT * FROM foo")
    assert list(rows) == [(1,), (2,), (3,)]


def test_timeit(db: pgtestdbpy.Config) -> None:
    import cProfile

    with cProfile.Profile() as pr:
        for _ in range(10):
            dummy_migrator = pgtestdbpy.Migrator("migrator", lambda _: None)
            # Approx 60ms per clone
            with pgtestdbpy.clone(db, dummy_migrator) as url:
                ...

    pr.dump_stats("clone.prof")
