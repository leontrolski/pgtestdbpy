from contextlib import contextmanager
from dataclasses import dataclass, replace
import pathlib
import random
import subprocess
import tempfile
from typing import Any, Callable, Iterator

import psycopg


Conn = psycopg.Connection[tuple[Any, ...]]

CMD_DB_INIT = "{initdb} -D {data_dir} --lc-messages=C -U postgres -A trust"
CMD_DB_START = "{pg_ctl} -D {data_dir} -l {log_file} -o '-p {port}' start"
CMD_DB_STOP = "{pg_ctl} -D {data_dir} stop"
CMD_HARD_KILL = "lsof -t -i:{port} | xargs kill"
URL = "postgres://{user}{password}@{host}:{port}/{db_name}"


@dataclass(frozen=True)
class InitConfig:
    user: str = "postgres"
    password: str | None = None
    host: str = "localhost"
    port: int = 8421
    db_name: str = "postgres"  # used for idempotency

    initdb: str = "initdb"
    pg_ctl: str = "pg_ctl"

    @property
    def url(self) -> str:
        return URL.format(
            user=self.user,
            password=":" + self.password if self.password else "",
            host=self.host,
            port=self.port,
            db_name=self.db_name,
        )


@dataclass(frozen=True)
class Migrator:
    db_name: str  # used for idempotency
    migrate: Callable[[Conn], None]
    user: str = "test"
    password: str = "test"
    host: str = "localhost"
    port: int = 8421

    @property
    def url(self) -> str:
        return URL.format(
            user=self.user,
            password=":" + self.password if self.password else "",
            host=self.host,
            port=self.port,
            db_name=self.db_name,
        )

    def clone(self) -> "Migrator":
        suffix = "".join(random.choice("abcdefghijklmnopqrstuvwxyz") for _ in range(16))
        return replace(self, db_name=f"{self.db_name}_{suffix}")


@contextmanager
def initdb(config: InitConfig = InitConfig()) -> Iterator[Conn]:
    with tempfile.TemporaryDirectory() as d:
        temp_path = pathlib.Path(d).resolve()
        data_dir = str(temp_path / "data")
        log_file = str(temp_path / "log.txt")
        subprocess.check_output(
            CMD_DB_INIT.format(initdb=config.initdb, data_dir=data_dir),
            shell=True,
        )
        subprocess.check_output(
            CMD_DB_START.format(
                pg_ctl=config.pg_ctl,
                data_dir=data_dir,
                log_file=log_file,
                port=config.port,
            ),
            shell=True,
        )
        try:
            with psycopg.connect(config.url, autocommit=True) as conn:
                yield conn
        finally:
            subprocess.check_output(
                CMD_DB_STOP.format(pg_ctl=config.pg_ctl, data_dir=data_dir),
                shell=True,
            )


QRY_USER_EXISTS = "SELECT EXISTS (SELECT from pg_catalog.pg_roles WHERE rolname = %s)"
QRY_USER_CREATE = 'CREATE ROLE "{user}"'
QRY_USER_ALTER = """ALTER ROLE "{user}" WITH LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE"""
QRY_TEMPLATE_EXISTS = "SELECT EXISTS (SELECT FROM pg_database WHERE datname = %s AND datistemplate = true)"
QRY_TEMPLATE_CREATE = 'CREATE DATABASE "{template}" OWNER "{user}"'
QRY_TEMPLATE_FINALIZE = "UPDATE pg_database SET datistemplate = true WHERE datname=%s"
QRY_DB_CLONE = 'CREATE DATABASE "{db_name}" WITH TEMPLATE "{template}" OWNER "{user}"'
QRY_DB_DROP = 'DROP DATABASE IF EXISTS "{db_name}"'


@contextmanager
def build_templates(admin_conn: Conn, migrators: list[Migrator]) -> Iterator[None]:
    c = admin_conn
    for m in migrators:
        [[user_exists]] = c.execute(QRY_USER_EXISTS, [m.user])
        if not user_exists:
            c.execute(QRY_USER_CREATE.format(user=m.user))
            c.execute(QRY_USER_ALTER.format(user=m.user, password=m.password))
        [[template_exists]] = c.execute(QRY_TEMPLATE_EXISTS, [m.db_name])
        if not template_exists:
            c.execute(QRY_TEMPLATE_CREATE.format(template=m.db_name, user=m.user))
            with psycopg.connect(m.url) as conn:
                m.migrate(conn)
            c.execute(QRY_TEMPLATE_FINALIZE, [m.db_name])

    yield


@contextmanager
def clone(admin_conn: Conn, migrator: Migrator) -> Iterator[Conn]:
    clone = migrator.clone()
    admin_conn.execute(
        QRY_DB_CLONE.format(
            db_name=clone.db_name, template=migrator.db_name, user=migrator.user
        )
    )
    with psycopg.connect(clone.url, autocommit=True) as conn:
        yield conn

    admin_conn.execute(QRY_DB_DROP.format(db_name=clone.db_name))
