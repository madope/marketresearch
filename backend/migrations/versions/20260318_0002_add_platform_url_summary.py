"""add platform url and summary

Revision ID: 20260318_0002
Revises: 20260316_0001
Create Date: 2026-03-18 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260318_0002"
down_revision = "20260316_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("research_platforms", sa.Column("platform_url", sa.Text(), nullable=True))
    op.add_column("research_platforms", sa.Column("platform_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("research_platforms", "platform_summary")
    op.drop_column("research_platforms", "platform_url")
