"""Create dataset and future rule configuration tables.

Revision ID: 0001_database_foundation
Revises:
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_database_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=True),
        sa.Column("source_hash", sa.String(length=64), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("duplicate_count", sa.Integer(), nullable=False),
        sa.Column("columns", sa.JSON(), nullable=False),
        sa.Column("category_column_added", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_hash"),
    )
    op.create_index("ix_datasets_owner_id", "datasets", ["owner_id"], unique=False)
    op.create_table(
        "expense_rows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("record_key", sa.String(length=64), nullable=False),
        sa.Column("dataset_id", sa.String(length=36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=120), nullable=False),
        sa.Column("who", sa.String(length=120), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["datasets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_key"),
    )
    op.create_index(
        "ix_expense_rows_dataset_id", "expense_rows", ["dataset_id"], unique=False
    )
    op.create_index(
        "ix_expense_rows_transaction_date",
        "expense_rows",
        ["transaction_date"],
        unique=False,
    )
    op.create_index(
        "ix_expense_rows_category", "expense_rows", ["category"], unique=False
    )
    op.create_index("ix_expense_rows_who", "expense_rows", ["who"], unique=False)
    for table_name in ("category_rule_sets", "who_rule_sets"):
        op.create_table(
            table_name,
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("owner_id", sa.String(length=36), nullable=True),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("rules", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            f"ix_{table_name}_owner_id", table_name, ["owner_id"], unique=False
        )


def downgrade() -> None:
    for table_name in ("category_rule_sets", "who_rule_sets"):
        op.drop_index(f"ix_{table_name}_owner_id", table_name=table_name)
        op.drop_table(table_name)
    op.drop_index("ix_expense_rows_dataset_id", table_name="expense_rows")
    op.drop_index("ix_expense_rows_transaction_date", table_name="expense_rows")
    op.drop_index("ix_expense_rows_category", table_name="expense_rows")
    op.drop_index("ix_expense_rows_who", table_name="expense_rows")
    op.drop_table("expense_rows")
    op.drop_index("ix_datasets_owner_id", table_name="datasets")
    op.drop_table("datasets")
