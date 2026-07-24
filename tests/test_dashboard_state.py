"""Unit tests for dashboard state derivation and API."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dashboard.server import app
from dashboard.state import build_case_state, derive_phase_status, read_artifact

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_CASE = PROJECT_ROOT / "cases" / "_example"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_derive_phase_status_example_case():
    outputs = EXAMPLE_CASE / "outputs"
    phases = derive_phase_status(outputs)
    assert phases["intake"] == "done"
    assert phases["plan"] == "done"
    assert phases["design"] == "done"
    assert phases["code"] == "done"
    assert phases["approval"] == "done"
    assert phases["sizing"] == "done"
    assert phases["output"] == "done"


def test_build_case_state_example_has_atlas(client: TestClient):
    state = build_case_state("_example")
    assert state["case"] == "_example"
    assert state["approvalStatus"] == "approved"
    assert state["mode"] == "agent"
    assert state["atlas"] is not None
    assert state["atlas"]["diskRequired"] is not None
    assert state["atlas"]["ramRequired"] is not None


def test_api_state_example(client: TestClient):
    res = client.get("/api/state", params={"case": "_example"})
    assert res.status_code == 200
    data = res.json()
    assert data["approvalStatus"] == "approved"
    assert "phases" in data
    assert len(data["artifacts"]) >= 5


def test_api_state_missing_case(client: TestClient):
    res = client.get("/api/state", params={"case": "nonexistent_case_xyz"})
    assert res.status_code == 404


def test_api_artifact_data_model(client: TestClient):
    res = client.get(
        "/api/artifact",
        params={"case": "_example", "name": "data-model.md"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "data-model.md"
    assert "Approval status" in data["content"] or "approved" in data["content"]


def test_api_artifact_not_previewable(client: TestClient):
    res = client.get(
        "/api/artifact",
        params={"case": "_example", "name": "seed.py"},
    )
    assert res.status_code == 404


def test_post_event_and_stream(client: TestClient):
    res = client.post("/events", json={"type": "test_ping", "detail": "hello"})
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_derive_phase_status_pending_approval(tmp_path: Path):
    case = tmp_path / "case"
    inputs = case / "inputs"
    outputs = case / "outputs"
    inputs.mkdir(parents=True)
    outputs.mkdir(parents=True)
    (inputs / "intake.json").write_text('{"useCaseName": "Test"}')
    (outputs / "session.json").write_text('{"agent_id": "agent-test"}')
    (outputs / "data-model.md").write_text("**Approval status:** pending\n")
    (outputs / "sizing_inputs.json").write_text("{}")

    phases = derive_phase_status(outputs)
    assert phases["intake"] == "done"
    assert phases["plan"] == "done"
    assert phases["design"] == "done"
    assert phases["code"] == "active"
    assert phases["approval"] == "pending"


def test_read_artifact_whitelist():
    content = read_artifact("_example", "data-model.md")
    assert content is not None
    assert read_artifact("_example", "seed.py") is None
