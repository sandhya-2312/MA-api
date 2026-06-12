"""Idempotent helpers for Alembic on DBs partially created via SQLAlchemy create_all."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


def _inspector():
    return inspect(op.get_bind())


def has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def has_column(table_name: str, column_name: str) -> bool:
    if not has_table(table_name):
        return False
    return column_name in {column["name"] for column in _inspector().get_columns(table_name)}


def has_index(table_name: str, index_name: str) -> bool:
    if not has_table(table_name):
        return False
    return index_name in {index["name"] for index in _inspector().get_indexes(table_name)}


def has_foreign_key(table_name: str, constraint_name: str) -> bool:
    if not has_table(table_name):
        return False
    return constraint_name in {fk["name"] for fk in _inspector().get_foreign_keys(table_name)}


def add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not has_table(table_name):
        return
    if not has_column(table_name, column.name):
        op.add_column(table_name, column)
