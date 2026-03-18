from collections.abc import Callable

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models.research import ResearchTask
from app.schemas.research import (
    CancelResearchTasksResponse,
    CreateResearchTaskRequest,
    CreateResearchTaskResponse,
    PlatformResponse,
    ProductResponse,
    ResearchTaskDetailResponse,
    ResearchTaskStatusResponse,
    StageStatusResponse,
    TaskSummaryResponse,
)
from app.services.research_service import cancel_all_tasks, create_task, get_task, list_tasks, run_task

router = APIRouter()
TaskExecutor = Callable[[str], None]

def get_task_executor() -> TaskExecutor:
    def _execute(task_id: str) -> None:
        db = SessionLocal()
        try:
            run_task(db, task_id)
        finally:
            db.close()

    return _execute


def _serialize_task(task: ResearchTask) -> TaskSummaryResponse:
    return TaskSummaryResponse(
        task_id=task.id,
        prompt=task.user_input,
        status=task.status,
        summary=task.summary,
        created_at=task.created_at,
    )


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/research-tasks", response_model=CreateResearchTaskResponse, status_code=status.HTTP_201_CREATED)
def create_research_task(
    payload: CreateResearchTaskRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    task_executor: TaskExecutor = Depends(get_task_executor),
) -> CreateResearchTaskResponse:
    task = create_task(db, payload.prompt)
    background_tasks.add_task(task_executor, task.id)
    return CreateResearchTaskResponse(task_id=task.id, status="queued")


@router.post("/research-tasks/cancel-all", response_model=CancelResearchTasksResponse)
def cancel_research_tasks(db: Session = Depends(get_db)) -> CancelResearchTasksResponse:
    cancelled_count = cancel_all_tasks(db)
    return CancelResearchTasksResponse(status="cancelled", cancelled_count=cancelled_count)


@router.get("/research-tasks", response_model=list[TaskSummaryResponse])
def get_research_tasks(db: Session = Depends(get_db)) -> list[TaskSummaryResponse]:
    return [_serialize_task(task) for task in list_tasks(db)]


@router.get("/research-tasks/{task_id}/status", response_model=ResearchTaskStatusResponse)
def get_research_task_status(task_id: str, db: Session = Depends(get_db)) -> ResearchTaskStatusResponse:
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return ResearchTaskStatusResponse(
        task_id=task.id,
        status=task.status,
        stages=[
            StageStatusResponse(
                workflow_name=stage.workflow_name,
                stage_name=stage.stage_name,
                status=stage.status,
                message=stage.message,
                retry_count=stage.retry_count,
                detail_json=stage.detail_json,
            )
            for stage in task.stages
        ],
    )


@router.get("/research-tasks/{task_id}", response_model=ResearchTaskDetailResponse)
def get_research_task_detail(task_id: str, db: Session = Depends(get_db)) -> ResearchTaskDetailResponse:
    task = get_task(db, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return ResearchTaskDetailResponse(
        task=_serialize_task(task),
        products=[
            ProductResponse(
                product_name=product.product_name,
                source_type=product.source_type,
                input_order=product.input_order,
            )
            for product in task.products
        ],
        platforms=[
            PlatformResponse(
                platform_name=platform.platform_name,
                platform_domain=platform.platform_domain,
                platform_url=platform.platform_url,
                platform_summary=platform.platform_summary,
                discover_round=platform.discover_round,
                platform_type=platform.platform_type,
            )
            for platform in task.platforms
        ],
        price_report=task.price_report.report_json if task.price_report else None,
        market_analysis={
            "revenue_model_text": task.market_analysis_report.revenue_model_text,
            "competition_text": task.market_analysis_report.competition_text,
            "build_plan_text": task.market_analysis_report.build_plan_text,
            "summary_json": task.market_analysis_report.summary_json,
        }
        if task.market_analysis_report
        else None,
        stages=[
            StageStatusResponse(
                workflow_name=stage.workflow_name,
                stage_name=stage.stage_name,
                status=stage.status,
                message=stage.message,
                retry_count=stage.retry_count,
                detail_json=stage.detail_json,
            )
            for stage in task.stages
        ],
    )
