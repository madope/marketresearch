from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.research import ResearchTask, ResearchTaskStage
from app.services.research_service import cancel_all_tasks, create_task, get_task, run_task


def test_run_task_persists_stage_updates_incrementally(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    task = create_task(db, "调研宠物烘干箱市场")

    class FakeGraph:
        def stream(self, state, stream_mode="updates"):
            assert stream_mode == ["tasks", "updates"]

            yield (
                "tasks",
                {
                    "id": "task-1",
                    "name": "parse_product_intent",
                    "input": state,
                    "triggers": ["start:parse_product_intent"],
                },
            )

            check_db = TestingSessionLocal()
            try:
                stages = check_db.query(ResearchTaskStage).filter(ResearchTaskStage.task_id == task.id).all()
                assert len(stages) == 1
                assert stages[0].stage_name == "parse_product_intent"
                assert stages[0].status == "running"
                assert stages[0].detail_json == {
                    "node_name": "parse_product_intent",
                    "status": "running",
                }
            finally:
                check_db.close()

            yield (
                "updates",
                {
                "parse_product_intent": {
                    "products": [
                        {"product_name": "宠物烘干箱", "source_type": "category_inferred", "input_order": 1}
                    ],
                    "stages": [
                        {
                            "workflow_name": "price_research",
                            "stage_name": "parse_product_intent",
                            "status": "completed",
                            "message": "已识别产品",
                            "retry_count": 0,
                            "detail_json": {
                                "intent_type": "category",
                                "products": [
                                    {
                                        "product_name": "宠物烘干箱",
                                        "source_type": "category_inferred",
                                        "input_order": 1,
                                    }
                                ],
                            },
                        }
                    ],
                },
            },
            )

            check_db = TestingSessionLocal()
            try:
                stages = check_db.query(ResearchTaskStage).filter(ResearchTaskStage.task_id == task.id).all()
                assert len(stages) == 1
                assert [stage.status for stage in stages] == ["completed"]
                assert stages[0].detail_json == {
                    "intent_type": "category",
                    "products": [
                        {
                            "product_name": "宠物烘干箱",
                            "source_type": "category_inferred",
                            "input_order": 1,
                        }
                    ],
                }
            finally:
                check_db.close()

            yield (
                "tasks",
                {
                    "id": "task-2",
                    "name": "discover_platforms",
                    "input": state,
                    "triggers": ["parse_product_intent"],
                },
            )

            check_db = TestingSessionLocal()
            try:
                stages = check_db.query(ResearchTaskStage).filter(ResearchTaskStage.task_id == task.id).all()
                assert len(stages) == 2
                stage_names = [stage.stage_name for stage in stages]
                statuses = [stage.status for stage in stages]
                assert stage_names == ["parse_product_intent", "discover_platforms"]
                assert statuses == ["completed", "running"]
            finally:
                check_db.close()

            yield (
                "updates",
                {
                "finalize_summary": {
                    "summary": "完成",
                },
                "discover_platforms": {
                    "platforms": [
                        {
                            "platform_name": "京东",
                            "platform_domain": "jd.com",
                            "discover_round": 1,
                            "platform_type": "marketplace",
                        }
                    ],
                    "stages": [
                        {
                            "workflow_name": "price_research",
                            "stage_name": "discover_platforms",
                            "status": "completed",
                            "message": "已发现平台",
                            "retry_count": 0,
                            "detail_json": {
                                "platforms": [
                                    {
                                        "platform_name": "京东",
                                        "platform_domain": "jd.com",
                                        "discover_round": 1,
                                        "platform_type": "marketplace",
                                    }
                                ]
                            },
                        }
                    ],
                },
                "crawl_prices_parallel": {
                    "price_records": [],
                    "stages": [],
                },
                "analyze_prices": {
                    "price_report": {
                        "currency": "CNY",
                        "sample_size": 0,
                        "platform_count": 1,
                        "average_price": 0,
                        "highest_price": 0,
                        "lowest_price": 0,
                        "fallback_used": True,
                        "warnings": [],
                        "source_breakdown": {},
                        "platform_source_breakdown": {},
                        "rows": [],
                    },
                    "stages": [],
                },
                "build_from_zero_plan": {
                    "market_analysis": {
                        "revenue_model_text": "收入",
                        "competition_text": "竞争",
                        "build_plan_text": "计划",
                        "summary_json": {},
                    },
                    "stages": [],
                },
            },
            )

    monkeypatch.setattr("app.services.research_service.get_research_graph", lambda: FakeGraph())

    run_task(db, task.id)

    stored_task = get_task(db, task.id)
    assert stored_task is not None
    assert stored_task.status == "completed"
    assert len(stored_task.stages) == 2


def test_cancel_all_tasks_cancels_queued_and_running_tasks() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    queued_task = create_task(db, "调研智能猫砂盆")
    running_task = create_task(db, "调研宠物烘干箱市场")
    running_task.status = "running"
    db.commit()

    cancelled_count = cancel_all_tasks(db)

    assert cancelled_count == 2
    refreshed_running = get_task(db, running_task.id)
    refreshed_queued = get_task(db, queued_task.id)
    assert refreshed_running is not None
    assert refreshed_queued is not None
    assert refreshed_running.status == "cancelled"
    assert refreshed_queued.status == "cancelled"
    running_cancel_stages = (
        db.query(ResearchTaskStage)
        .filter(ResearchTaskStage.task_id == running_task.id, ResearchTaskStage.stage_name == "cancel_task")
        .all()
    )
    assert len(running_cancel_stages) == 1


def test_run_task_stops_when_task_is_cancelled_mid_stream(monkeypatch) -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    task = create_task(db, "调研宠物烘干箱市场")

    class FakeGraph:
        def stream(self, state, stream_mode="updates"):
            assert stream_mode == ["tasks", "updates"]

            yield (
                "tasks",
                {
                    "id": "task-1",
                    "name": "parse_product_intent",
                    "input": state,
                    "triggers": ["start:parse_product_intent"],
                },
            )

            yield (
                "updates",
                {
                "parse_product_intent": {
                    "products": [
                        {"product_name": "宠物烘干箱", "source_type": "category_inferred", "input_order": 1}
                    ],
                    "stages": [
                        {
                            "workflow_name": "price_research",
                            "stage_name": "parse_product_intent",
                            "status": "completed",
                            "message": "已识别产品",
                            "retry_count": 0,
                            "detail_json": {
                                "intent_type": "category",
                                "products": [
                                    {
                                        "product_name": "宠物烘干箱",
                                        "source_type": "category_inferred",
                                        "input_order": 1,
                                    }
                                ],
                            },
                        }
                    ],
                },
            },
            )

            check_db = TestingSessionLocal()
            try:
                cancelled_task = check_db.get(ResearchTask, task.id)
                assert cancelled_task is not None
                cancelled_task.status = "cancelled"
                check_db.commit()
            finally:
                check_db.close()

            yield (
                "tasks",
                {
                    "id": "task-2",
                    "name": "discover_platforms",
                    "input": state,
                    "triggers": ["parse_product_intent"],
                },
            )

            yield (
                "updates",
                {
                "discover_platforms": {
                    "platforms": [
                        {
                            "platform_name": "京东",
                            "platform_domain": "jd.com",
                            "discover_round": 1,
                            "platform_type": "marketplace",
                        }
                    ],
                    "stages": [
                        {
                            "workflow_name": "price_research",
                            "stage_name": "discover_platforms",
                            "status": "completed",
                            "message": "已发现平台",
                            "retry_count": 0,
                        }
                    ],
                },
            },
            )

    monkeypatch.setattr("app.services.research_service.get_research_graph", lambda: FakeGraph())

    run_task(db, task.id)

    stored_task = get_task(db, task.id)
    assert stored_task is not None
    assert stored_task.status == "cancelled"
    assert stored_task.price_report is None
    assert [stage.stage_name for stage in stored_task.stages] == ["parse_product_intent"]
