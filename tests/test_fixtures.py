import pgtestdbpy


def test_insert_and_select(conn: pgtestdbpy.Conn) -> None:
    conn.execute("INSERT INTO foo (a) VALUES (1), (2), (3)")
    rows = conn.execute("SELECT * FROM foo")
    assert list(rows) == [(1,), (2,), (3,)]


# 50 takes 5s = 100ms per clone


def test_timeit(admin_conn: pgtestdbpy.Conn) -> None:
    import cProfile

    with cProfile.Profile() as pr:
        dummy_migrator = pgtestdbpy.Migrator("migrator1", lambda _: None)
        with pgtestdbpy.clone(admin_conn, dummy_migrator) as conn_:
            ...

    pr.dump_stats("clone.prof")
