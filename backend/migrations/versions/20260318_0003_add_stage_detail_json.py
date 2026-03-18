"""add stage detail json

Revision ID: 20260318_0003
Revises: 20260318_0002
Create Date: 2026-03-18 14:40:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260318_0003"
down_revision = "20260318_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("research_task_stages", sa.Column("detail_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("research_task_stages", "detail_json")
