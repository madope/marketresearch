"""initial schema

Revision ID: 20260316_0001
Revises:
Create Date: 2026-03-16 18:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260316_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_input", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "research_products",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("input_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_products_task_id", "research_products", ["task_id"], unique=False)
    op.create_table(
        "research_platforms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("platform_name", sa.String(length=255), nullable=False),
        sa.Column("platform_domain", sa.String(length=255), nullable=False),
        sa.Column("discover_round", sa.Integer(), nullable=False),
        sa.Column("platform_type", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_platforms_task_id", "research_platforms", ["task_id"], unique=False)
    op.create_table(
        "research_task_stages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("workflow_name", sa.String(length=64), nullable=False),
        sa.Column("stage_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_task_stages_task_id", "research_task_stages", ["task_id"], unique=False)
    op.create_table(
        "market_analysis_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("revenue_model_text", sa.Text(), nullable=False),
        sa.Column("competition_text", sa.Text(), nullable=False),
        sa.Column("build_plan_text", sa.Text(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_table(
        "price_reports",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_table(
        "price_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("platform_id", sa.Integer(), nullable=True),
        sa.Column("product_url", sa.Text(), nullable=True),
        sa.Column("raw_title", sa.Text(), nullable=True),
        sa.Column("spec_text", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=False),
        sa.Column("raw_price", sa.Float(), nullable=True),
        sa.Column("normalized_price", sa.Float(), nullable=True),
        sa.Column("price_unit", sa.String(length=64), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("is_outlier", sa.Boolean(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["platform_id"], ["research_platforms.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["research_products.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["research_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_records_task_id", "price_records", ["task_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_price_records_task_id", table_name="price_records")
    op.drop_table("price_records")
    op.drop_table("price_reports")
    op.drop_table("market_analysis_reports")
    op.drop_index("ix_research_task_stages_task_id", table_name="research_task_stages")
    op.drop_table("research_task_stages")
    op.drop_index("ix_research_platforms_task_id", table_name="research_platforms")
    op.drop_table("research_platforms")
    op.drop_index("ix_research_products_task_id", table_name="research_products")
    op.drop_table("research_products")
    op.drop_table("research_tasks")
