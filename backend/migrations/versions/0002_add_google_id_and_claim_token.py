"""Add google_id to users and claim_token to reports.

Revision ID: 0002_add_google_id_and_claim_token
Revises: 0001_initial
Create Date: 2026-10-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_add_google_id_and_claim_token"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add google_id to users
    try:
        op.add_column("users", sa.Column("google_id", sa.String(length=128), nullable=True))
        op.create_index(op.f("ix_users_google_id"), "users", ["google_id"], unique=True)
    except Exception:
        pass

    # Add claim_token to reports
    try:
        op.add_column("reports", sa.Column("claim_token", sa.String(length=64), nullable=True))
        op.create_index(op.f("ix_reports_claim_token"), "reports", ["claim_token"], unique=False)
    except Exception:
        pass


def downgrade() -> None:
    try:
        op.drop_index(op.f("ix_reports_claim_token"), table_name="reports")
        op.drop_column("reports", "claim_token")
    except Exception:
        pass

    try:
        op.drop_index(op.f("ix_users_google_id"), table_name="users")
        op.drop_column("users", "google_id")
    except Exception:
        pass
