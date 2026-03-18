from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _json_type() -> type[JSON]:
    return JSON


class ResearchTask(Base):
    __tablename__ = "research_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_input: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    stages: Mapped[list["ResearchTaskStage"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    products: Mapped[list["ResearchProduct"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    platforms: Mapped[list["ResearchPlatform"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    price_records: Mapped[list["PriceRecord"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
    )
    price_report: Mapped["PriceReport | None"] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        uselist=False,
    )
    market_analysis_report: Mapped["MarketAnalysisReport | None"] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        uselist=False,
    )


class ResearchTaskStage(Base):
    __tablename__ = "research_task_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("research_tasks.id"), nullable=False, index=True)
    workflow_name: Mapped[str] = mapped_column(String(64), nullable=False)
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail_json: Mapped[dict[str, Any] | None] = mapped_column(_json_type(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    task: Mapped[ResearchTask] = relationship(back_populates="stages")


class ResearchProduct(Base):
    __tablename__ = "research_products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("research_tasks.id"), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    input_order: Mapped[int] = mapped_column(Integer, nullable=False)

    task: Mapped[ResearchTask] = relationship(back_populates="products")


class ResearchPlatform(Base):
    __tablename__ = "research_platforms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("research_tasks.id"), nullable=False, index=True)
    platform_name: Mapped[str] = mapped_column(String(255), nullable=False)
    platform_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    platform_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    discover_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    platform_type: Mapped[str] = mapped_column(String(64), default="marketplace", nullable=False)

    task: Mapped[ResearchTask] = relationship(back_populates="platforms")


class PriceRecord(Base):
    __tablename__ = "price_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("research_tasks.id"), nullable=False, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("research_products.id"), nullable=True)
    platform_id: Mapped[int | None] = mapped_column(ForeignKey("research_platforms.id"), nullable=True)
    product_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    spec_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    currency: Mapped[str] = mapped_column(String(16), default="CNY", nullable=False)
    raw_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    normalized_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_unit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    task: Mapped[ResearchTask] = relationship(back_populates="price_records")


class PriceReport(Base):
    __tablename__ = "price_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("research_tasks.id"), nullable=False, unique=True)
    report_json: Mapped[dict[str, Any]] = mapped_column(_json_type(), nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    task: Mapped[ResearchTask] = relationship(back_populates="price_report")


class MarketAnalysisReport(Base):
    __tablename__ = "market_analysis_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("research_tasks.id"), nullable=False, unique=True)
    revenue_model_text: Mapped[str] = mapped_column(Text, nullable=False)
    competition_text: Mapped[str] = mapped_column(Text, nullable=False)
    build_plan_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[dict[str, Any]] = mapped_column(_json_type(), nullable=False)

    task: Mapped[ResearchTask] = relationship(back_populates="market_analysis_report")
