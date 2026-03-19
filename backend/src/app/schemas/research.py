from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CreateResearchTaskRequest(BaseModel):
    prompt: str = Field(min_length=3)


class IntakeMessage(BaseModel):
    role: str
    content: str = Field(min_length=1)


class ResearchRequirementDraft(BaseModel):
    market_topic: str = ""
    target_region: str = ""
    products: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class ResearchIntakeChatRequest(BaseModel):
    messages: list[IntakeMessage] = Field(default_factory=list)
    draft_requirement: ResearchRequirementDraft = Field(default_factory=ResearchRequirementDraft)


class ResearchIntakeChatResponse(BaseModel):
    assistant_message: str
    draft_requirement: ResearchRequirementDraft
    missing_fields: list[str]
    ready_to_start: bool
    final_prompt: str


class TaskSummaryResponse(BaseModel):
    task_id: str
    prompt: str
    status: str
    summary: str | None
    created_at: datetime


class CreateResearchTaskResponse(BaseModel):
    task_id: str
    status: str


class CancelResearchTasksResponse(BaseModel):
    status: str
    cancelled_count: int


class StageStatusResponse(BaseModel):
    workflow_name: str
    stage_name: str
    status: str
    message: str | None
    retry_count: int
    detail_json: dict[str, Any] | None = None


class ResearchTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    stages: list[StageStatusResponse]


class ProductResponse(BaseModel):
    product_name: str
    source_type: str
    input_order: int


class PlatformResponse(BaseModel):
    platform_name: str
    platform_domain: str
    platform_url: str | None = None
    platform_summary: str | None = None
    discover_round: int
    platform_type: str


class ResearchTaskDetailResponse(BaseModel):
    task: TaskSummaryResponse
    products: list[ProductResponse]
    platforms: list[PlatformResponse]
    price_report: dict[str, Any] | None
    market_analysis: dict[str, Any] | None
    stages: list[StageStatusResponse]
