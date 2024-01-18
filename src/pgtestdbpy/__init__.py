from contextlib import contextmanager
from dataclasses import dataclass, replace
import random
from typing import Any, Callable, Iterator

import psycopg

PsycoConn = psycopg.Connection[tuple[Any, ...]]
URL = "postgres://{user}{password}@{host}:{port}/{db_name}"


@dataclass(frozen=True)
class Config:
    user: str = "postgres"
    password: str = "password"
    host: str = "localhost"
    port: int = 5432
    db_name: str = "postgres"

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
    migrate: Callable[[str], None]
    db_name: str = "migrator"
    user: str = "test"
    password: str = "password"
    host: str = "localhost"
    port: int = 5432

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


QRY_USER_CREATE = 'CREATE ROLE "{user}"'
QRY_USER_DROP = 'DROP ROLE "{user}"'
QRY_USER_ALTER = """ALTER ROLE "{user}" WITH LOGIN PASSWORD '{password}' NOSUPERUSER NOCREATEDB NOCREATEROLE"""
QRY_TEMPLATE_CREATE = 'CREATE DATABASE "{template}" OWNER "{user}"'
QRY_TEMPLATE_FINALIZE = "UPDATE pg_database SET datistemplate = true WHERE datname=%s"
QRY_TEMPLATE_DEFINALIZE = (
    "UPDATE pg_database SET datistemplate = false WHERE datname=%s"
)
QRY_DB_CLONE = 'CREATE DATABASE "{db_name}" WITH TEMPLATE "{template}" OWNER "{user}" STRATEGY=FILE_COPY'  # FILE_COPY seems slightly faster
QRY_DB_DROP = 'DROP DATABASE IF EXISTS "{db_name}"'


@contextmanager
def templates(config: Config, migrator: Migrator) -> Iterator[None]:
    with psycopg.connect(config.url, autocommit=True) as c:
        c.execute(QRY_USER_CREATE.format(user=migrator.user))
        c.execute(QRY_USER_ALTER.format(user=migrator.user, password=migrator.password))
        c.execute(
            QRY_TEMPLATE_CREATE.format(template=migrator.db_name, user=migrator.user)
        )
        migrator.migrate(migrator.url)
        c.execute(QRY_TEMPLATE_FINALIZE, [migrator.db_name])
        try:
            yield
        finally:
            c.execute(QRY_TEMPLATE_DEFINALIZE, [migrator.db_name])
            c.execute(QRY_DB_DROP.format(db_name=migrator.db_name))
            c.execute(QRY_USER_DROP.format(user=migrator.user))


@contextmanager
def clone(config: Config, migrator: Migrator) -> Iterator[str]:
    clone = migrator.clone()
    with psycopg.connect(config.url, autocommit=True) as c:
        c.execute(
            QRY_DB_CLONE.format(
                db_name=clone.db_name, template=migrator.db_name, user=migrator.user
            )
        )
        try:
            yield clone.url
        finally:
            c.execute(QRY_DB_DROP.format(db_name=clone.db_name))
