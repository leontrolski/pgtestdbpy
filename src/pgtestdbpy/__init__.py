from contextlib import contextmanager
from dataclasses import dataclass, replace
import pathlib
import random
import subprocess
import tempfile
from typing import Any, Callable, Iterator

import psycopg

PsycoConn = psycopg.Connection[tuple[Any, ...]]

CMD_DB_INIT = "{initdb} -D {data_dir} --lc-messages=C --data-checksums --no-sync -U postgres -A trust"
CMD_DB_START = "{pg_ctl} -D {data_dir} -l {log_file} -o '-p {port}' start"
CMD_DB_STOP = "{pg_ctl} -D {data_dir} stop"
CMD_HARD_KILL = "lsof -t -i:{port} | xargs kill"
URL = "postgres://{user}{password}@{host}:{port}/{db_name}"


@dataclass(frozen=True)
class Config:
    user: str = "postgres"
    password: str | None = None
    host: str = "localhost"
    port: int = 8421
    db_name: str = "postgres"

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
    migrate: Callable[[str], None]
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
def initdb(config: Config) -> Iterator[None]:
    # On a Mac, if we run the following command before, we can run against a ramdisk
    #   diskutil erasevolume HFS+ postgres-ram-disk $(hdiutil attach -nomount ram://1048576)
    dir: str | None = "/Volumes/postgres-ram-disk"
    if not pathlib.Path(dir).exists():  #  type:ignore[arg-type]
        dir = None
    with tempfile.TemporaryDirectory(dir=dir) as d:
        temp_path = pathlib.Path(d).resolve()
        data_dir = str(temp_path / "data")
        log_file = str(temp_path / "log.txt")
        subprocess.check_output(
            CMD_DB_INIT.format(initdb=config.initdb, data_dir=data_dir),
            shell=True,
        )
        conf_file = temp_path / "data/postgresql.conf"
        conf_file.write_text(conf_file.read_text() + POSTGRES_CONF)
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
            yield
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
QRY_DB_CLONE = 'CREATE DATABASE "{db_name}" WITH TEMPLATE "{template}" OWNER "{user}" STRATEGY=FILE_COPY'  # FILE_COPY seems slightly faster
QRY_DB_DROP = 'DROP DATABASE IF EXISTS "{db_name}"'


def build_templates(config: Config, migrators: list[Migrator]) -> None:
    with psycopg.connect(config.url, autocommit=True) as c:
        for m in migrators:
            [[user_exists]] = c.execute(QRY_USER_EXISTS, [m.user])
            if not user_exists:
                c.execute(QRY_USER_CREATE.format(user=m.user))
                c.execute(QRY_USER_ALTER.format(user=m.user, password=m.password))
            [[template_exists]] = c.execute(QRY_TEMPLATE_EXISTS, [m.db_name])
            if not template_exists:
                c.execute(QRY_TEMPLATE_CREATE.format(template=m.db_name, user=m.user))
                m.migrate(m.url)
                c.execute(QRY_TEMPLATE_FINALIZE, [m.db_name])


@contextmanager
def clone(config: Config, migrator: Migrator) -> Iterator[str]:
    clone = migrator.clone()
    clone_sql = QRY_DB_CLONE.format(
        db_name=clone.db_name, template=migrator.db_name, user=migrator.user
    )
    # subprocess.check_output(f"psql {config.url} -c '{clone_sql}'", shell=True)
    with psycopg.connect(config.url, autocommit=True) as c:
        c.execute(clone_sql)
        yield clone.url
        c.execute(QRY_DB_DROP.format(db_name=clone.db_name))


POSTGRES_CONF = """
shared_buffers = 128MB         # Amount of memory used for caching data
effective_cache_size = 1GB     # Estimated size of the disk cache
work_mem = 64MB                # Maximum amount of memory used for internal sort operations
# wal_level = minimal          # Minimal level of WAL logging
fsync = off                    # Disable synchronous commits
synchronous_commit = off       # Disable synchronous replication
full_page_writes = off         # Disable full-page writes
wal_sync_method = open_sync    # Open synchronous writes
max_connections = 100
client_min_messages = warning
checkpoint_timeout = 10min     # Time between automatic checkpoints
checkpoint_completion_target = 0.9   # Target duration for completing checkpoints
autovacuum = off               # Disable automatic vacuuming
logging_collector = off        # Disable the logging collector
"""
