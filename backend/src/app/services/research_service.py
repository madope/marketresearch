from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.research import (
    MarketAnalysisReport,
    PriceRecord,
    PriceReport,
    ResearchPlatform,
    ResearchProduct,
    ResearchTask,
    ResearchTaskStage,
)
from app.workflows.research_workflow import WorkflowResult, get_research_graph


class TaskCancelledError(Exception):
    pass


def create_task(db: Session, prompt: str) -> ResearchTask:
    task = ResearchTask(user_input=prompt, status="queued")
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session) -> list[ResearchTask]:
    return db.query(ResearchTask).order_by(ResearchTask.created_at.desc()).all()


def get_task(db: Session, task_id: str) -> ResearchTask | None:
    return db.get(ResearchTask, task_id)


def cancel_all_tasks(db: Session) -> int:
    tasks = (
        db.query(ResearchTask)
        .filter(ResearchTask.status.in_(("queued", "running")))
        .order_by(ResearchTask.created_at.desc())
        .all()
    )
    now = datetime.utcnow()
    cancelled_count = 0
    for task in tasks:
        was_running = task.status == "running"
        task.status = "cancelled"
        task.finished_at = now
        cancelled_count += 1
        if was_running:
            db.add(
                ResearchTaskStage(
                    task_id=task.id,
                    workflow_name="system",
                    stage_name="cancel_task",
                    status="cancelled",
                    message="用户已中止调研任务",
                    retry_count=0,
                    started_at=now,
                    finished_at=now,
                )
            )
    db.commit()
    return cancelled_count


def _persist_stage_updates(db: Session, task_id: str, stages: list[dict[str, object]]) -> None:
    for stage in stages:
        stage_status = str(stage["status"])
        if stage_status == "running":
            db.query(ResearchTaskStage).filter(
                ResearchTaskStage.task_id == task_id,
                ResearchTaskStage.workflow_name == str(stage["workflow_name"]),
                ResearchTaskStage.stage_name == str(stage["stage_name"]),
            ).delete()
        else:
            db.query(ResearchTaskStage).filter(
                ResearchTaskStage.task_id == task_id,
                ResearchTaskStage.workflow_name == str(stage["workflow_name"]),
                ResearchTaskStage.stage_name == str(stage["stage_name"]),
                ResearchTaskStage.status == "running",
            ).delete()
        db.add(
            ResearchTaskStage(
                task_id=task_id,
                workflow_name=str(stage["workflow_name"]),
                stage_name=str(stage["stage_name"]),
                status=stage_status,
                message=str(stage["message"]) if stage.get("message") is not None else None,
                detail_json=stage.get("detail_json"),
                retry_count=int(stage.get("retry_count", 0)),
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
            )
        )
    db.commit()


def _merge_workflow_update(aggregated: dict[str, object], update: dict[str, object]) -> None:
    for key, value in update.items():
        if key == "stages":
            aggregated.setdefault("stages", [])
            aggregated["stages"].extend(value)
        elif key == "market_analysis":
            existing = dict(aggregated.get("market_analysis", {}))
            existing.update(value)
            aggregated["market_analysis"] = existing
        else:
            aggregated[key] = value


def _workflow_name_for_node(node_name: str) -> str:
    return (
        "market_analysis"
        if node_name
        in {
            "extract_business_topic",
            "analyze_revenue_model",
            "analyze_competition_and_outlook",
            "build_from_zero_plan",
        }
        else "price_research"
    )


def _clear_running_stages(db: Session, task_id: str) -> None:
    db.query(ResearchTaskStage).filter(
        ResearchTaskStage.task_id == task_id,
        ResearchTaskStage.status == "running",
    ).delete()
    db.commit()


def _ensure_task_not_cancelled(db: Session, task_id: str) -> None:
    db.expire_all()
    task = get_task(db, task_id)
    if task is not None and task.status == "cancelled":
        raise TaskCancelledError()


def _persist_running_stage(db: Session, task_id: str, node_name: str) -> None:
    running_stage = {
        "workflow_name": _workflow_name_for_node(node_name),
        "stage_name": node_name,
        "status": "running",
        "message": "执行中",
        "detail_json": {
            "node_name": node_name,
            "status": "running",
        },
        "retry_count": 0,
    }
    _persist_stage_updates(db, task_id, [running_stage])


def _run_research_workflow_streaming(db: Session, task_id: str, prompt: str) -> WorkflowResult:
    aggregated: dict[str, object] = {"stages": []}
    graph = get_research_graph()

    db.query(ResearchTaskStage).filter(ResearchTaskStage.task_id == task_id).delete()
    db.commit()

    for mode, payload in graph.stream(
        {"prompt": prompt, "stages": []},
        stream_mode=["tasks", "updates"],
    ):
        if mode == "tasks":
            if isinstance(payload, dict) and "triggers" in payload and "name" in payload:
                _persist_running_stage(db, task_id, str(payload["name"]))
        elif mode == "updates":
            for node_name, node_output in payload.items():
                stages = list(node_output.get("stages", []))
                if stages:
                    _persist_stage_updates(db, task_id, stages)
                _merge_workflow_update(aggregated, node_output)
        _ensure_task_not_cancelled(db, task_id)

    return WorkflowResult(
        products=list(aggregated.get("products", [])),
        platforms=list(aggregated.get("platforms", [])),
        price_records=list(aggregated.get("price_records", [])),
        price_report=dict(aggregated.get("price_report", {})),
        market_analysis=dict(aggregated.get("market_analysis", {})),
        stages=list(aggregated.get("stages", [])),
        summary=str(aggregated.get("summary", "")),
    )


def run_task(db: Session, task_id: str) -> None:
    task = get_task(db, task_id)
    if task is None:
        return
    if task.status == "cancelled":
        return

    task.status = "running"
    task.started_at = datetime.utcnow()
    db.commit()
    try:
        result = _run_research_workflow_streaming(db, task_id, task.user_input)
    except TaskCancelledError:
        _clear_running_stages(db, task_id)
        task = get_task(db, task_id)
        if task is not None:
            task.status = "cancelled"
            task.finished_at = datetime.utcnow()
            db.commit()
        return

    task = get_task(db, task_id)
    if task is None or task.status == "cancelled":
        return

    db.query(ResearchProduct).filter(ResearchProduct.task_id == task_id).delete()
    for product in result.products:
        db.add(
            ResearchProduct(
                task_id=task_id,
                product_name=product["product_name"],
                source_type=product["source_type"],
                input_order=product["input_order"],
            )
        )

    db.query(ResearchPlatform).filter(ResearchPlatform.task_id == task_id).delete()
    for platform in result.platforms:
        db.add(
            ResearchPlatform(
                task_id=task_id,
                platform_name=platform["platform_name"],
                platform_domain=platform["platform_domain"],
                platform_url=platform.get("platform_url"),
                platform_summary=platform.get("platform_summary"),
                discover_round=platform["discover_round"],
                platform_type=platform["platform_type"],
            )
        )
    db.flush()
    product_rows = db.query(ResearchProduct).filter(ResearchProduct.task_id == task_id).all()
    platform_rows = db.query(ResearchPlatform).filter(ResearchPlatform.task_id == task_id).all()

    db.query(PriceRecord).filter(PriceRecord.task_id == task_id).delete()
    platform_map = {platform.platform_name: platform.id for platform in platform_rows}
    product_map = {product.product_name: product.id for product in product_rows}
    for row in result.price_records:
        db.add(
            PriceRecord(
                task_id=task_id,
                product_id=product_map.get(row["product_name"]),
                platform_id=platform_map.get(row["platform_name"]),
                product_url=row["product_url"],
                raw_title=row["raw_title"],
                spec_text=row["spec_text"],
                currency=row["currency"],
                raw_price=row["raw_price"],
                normalized_price=row["normalized_price"],
                price_unit=row["price_unit"],
                confidence_score=row["confidence_score"],
                is_outlier=row["is_outlier"],
            )
        )

    db.query(PriceReport).filter(PriceReport.task_id == task_id).delete()
    db.add(
        PriceReport(
            task_id=task_id,
            report_json=result.price_report,
            summary_text=result.summary,
        )
    )

    db.query(MarketAnalysisReport).filter(MarketAnalysisReport.task_id == task_id).delete()
    db.add(
        MarketAnalysisReport(
            task_id=task_id,
            revenue_model_text=result.market_analysis["revenue_model_text"],
            competition_text=result.market_analysis["competition_text"],
            build_plan_text=result.market_analysis["build_plan_text"],
            summary_json=result.market_analysis["summary_json"],
        )
    )

    task = get_task(db, task_id)
    if task is None or task.status == "cancelled":
        db.rollback()
        return

    _clear_running_stages(db, task_id)
    task.status = "completed"
    task.summary = result.summary
    task.finished_at = datetime.utcnow()
    db.commit()
