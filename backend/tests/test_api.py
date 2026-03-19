from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import get_task_executor
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.research import ResearchTask
from app.services.research_service import create_task, run_task


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_task_executor():
        def _execute(task_id: str) -> None:
            db = TestingSessionLocal()
            try:
                run_task(db, task_id)
            finally:
                db.close()

        return _execute

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_task_executor] = override_task_executor
    app.state.testing_session_factory = TestingSessionLocal
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    del app.state.testing_session_factory


def test_create_task_runs_workflow_and_returns_detail(client: TestClient) -> None:
    create_response = client.post(
        "/api/research-tasks",
        json={"prompt": "调研中国大陆宠物烘干箱市场"},
    )

    assert create_response.status_code == 201
    payload = create_response.json()
    assert payload["status"] == "queued"

    detail_response = client.get(f"/api/research-tasks/{payload['task_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()

    assert detail["task"]["status"] == "completed"
    assert len(detail["products"]) == 5
    assert len(detail["platforms"]) >= 0
    assert detail["price_report"]["sample_size"] >= 0
    assert "revenue_model_text" in detail["market_analysis"]
    assert any(stage["workflow_name"] == "price_research" for stage in detail["stages"])
    assert any(stage["message"] for stage in detail["stages"])
    assert any("产品" in stage["message"] or "平台" in stage["message"] for stage in detail["stages"] if stage["message"])
    assert any("detail_json" in stage for stage in detail["stages"])


def test_specific_product_list_keeps_exact_products(client: TestClient) -> None:
    create_response = client.post(
        "/api/research-tasks",
        json={"prompt": "iPhone 16, 华为 Mate 70, 小米 15"},
    )
    task_id = create_response.json()["task_id"]

    detail_response = client.get(f"/api/research-tasks/{task_id}")
    detail = detail_response.json()

    assert [item["product_name"] for item in detail["products"]] == [
        "iPhone 16",
        "华为 Mate 70",
        "小米 15",
    ]
    assert len(detail["products"]) == 3


def test_list_tasks_returns_latest_first(client: TestClient) -> None:
    client.post("/api/research-tasks", json={"prompt": "调研智能猫砂盆"})
    client.post("/api/research-tasks", json={"prompt": "调研电动牙刷"})

    response = client.get("/api/research-tasks")
    assert response.status_code == 200
    tasks = response.json()

    assert len(tasks) == 2
    assert tasks[0]["prompt"] == "调研电动牙刷"
    assert tasks[1]["prompt"] == "调研智能猫砂盆"


def test_cors_preflight_allows_frontend_origin(client: TestClient) -> None:
    response = client.options(
        "/api/research-tasks",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_cancel_all_tasks_marks_queued_and_running_tasks_as_cancelled(client: TestClient) -> None:
    session_factory = app.state.testing_session_factory
    original_executor_override = app.dependency_overrides[get_task_executor]

    def no_op_task_executor():
        def _execute(task_id: str) -> None:
            return None

        return _execute

    app.dependency_overrides[get_task_executor] = no_op_task_executor
    db = session_factory()
    try:
        queued_response = client.post("/api/research-tasks", json={"prompt": "调研智能猫砂盆"})
        assert queued_response.status_code == 201

        running_task = create_task(db, "调研电动牙刷")
        running_task.status = "running"
        db.commit()

        queued_task = db.get(ResearchTask, queued_response.json()["task_id"])
        assert queued_task is not None
        assert queued_task.status == "queued"
    finally:
        app.dependency_overrides[get_task_executor] = original_executor_override
        db.close()

    cancel_response = client.post("/api/research-tasks/cancel-all")

    assert cancel_response.status_code == 200
    payload = cancel_response.json()
    assert payload["status"] == "cancelled"
    assert payload["cancelled_count"] == 2

    verify_db = session_factory()
    try:
        stored_queued_task = verify_db.get(ResearchTask, queued_response.json()["task_id"])
        stored_running_task = verify_db.get(ResearchTask, running_task.id)
        assert stored_queued_task is not None
        assert stored_running_task is not None
        assert stored_queued_task.status == "cancelled"
        assert stored_running_task.status == "cancelled"
    finally:
        verify_db.close()


def test_research_intake_chat_returns_structured_requirement_and_follow_up(client: TestClient) -> None:
    response = client.post(
        "/api/research-intake/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "我想调研中国大陆宠物烘干箱市场，重点看价格和平台",
                }
            ],
            "draft_requirement": {
                "market_topic": "",
                "target_region": "",
                "products": [],
                "goals": [],
                "constraints": {},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["draft_requirement"]["target_region"] == "中国大陆"
    assert "宠物烘干箱" in payload["draft_requirement"]["products"]
    assert "价格调研" in payload["draft_requirement"]["goals"]
    assert "平台分布" in payload["draft_requirement"]["goals"]
    assert payload["ready_to_start"] is True
    assert "请点击下方按钮开始调研" in payload["assistant_message"]
    assert "调研中国大陆宠物烘干箱市场" in payload["final_prompt"]


def test_research_intake_chat_asks_follow_up_when_core_fields_are_missing(client: TestClient) -> None:
    response = client.post(
        "/api/research-intake/chat",
        json={
            "messages": [
                {
                    "role": "user",
                    "content": "我想调研宠物市场",
                }
            ],
            "draft_requirement": {
                "market_topic": "",
                "target_region": "",
                "products": [],
                "goals": [],
                "constraints": {},
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ready_to_start"] is False
    assert "target_region" in payload["missing_fields"]
    assert "products" in payload["missing_fields"]
    assert payload["assistant_message"]
