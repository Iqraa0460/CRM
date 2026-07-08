import json
import os
import pytest
from fastapi.testclient import TestClient

from database import SessionLocal, HCP, Material, Sample, Interaction, init_db
from main import app
from tools import search_hcp, search_materials_and_samples, generate_followups, log_interaction, edit_interaction
from agent import agent_graph

# Setup test DB environment
os.environ["DATABASE_URL"] = "sqlite:///./test_crm.db"

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    # Force initialize the DB
    init_db()
    yield
    # Clean up test DB file
    if os.path.exists("./test_crm.db"):
        try:
            os.remove("./test_crm.db")
        except PermissionError:
            pass

def test_db_seeding():
    db = SessionLocal()
    try:
        hcp_count = db.query(HCP).count()
        mat_count = db.query(Material).count()
        samp_count = db.query(Sample).count()
        
        assert hcp_count > 0, "HCP seeding failed"
        assert mat_count > 0, "Material seeding failed"
        assert samp_count > 0, "Sample seeding failed"
        
        # Verify specific seeded items
        hcp = db.query(HCP).filter(HCP.name == "Dr. Anita Sharma").first()
        assert hcp is not None
        assert hcp.specialty == "Oncology"
    finally:
        db.close()

def test_tool_search_hcp():
    res = search_hcp("Anita")
    data = json.loads(res)
    assert len(data) >= 1
    assert data[0]["name"] == "Dr. Anita Sharma"

def test_tool_search_materials_and_samples():
    res = search_materials_and_samples("OncoBoost")
    data = json.loads(res)
    assert "materials" in data
    assert "samples" in data
    assert len(data["materials"]) >= 1
    assert len(data["samples"]) >= 1

def test_tool_generate_followups():
    res = generate_followups("OncoBoost efficacy and dosage", "HCP interested in clinical trials")
    data = json.loads(res)
    assert "Send OncoBoost Phase III PDF" in data
    assert "Add Dr. Sharma to advisory board invite list" in data

def test_tool_log_and_edit_interaction():
    # Test logging interaction
    log_res = log_interaction(
        hcp_name="Dr. Anita Sharma",
        interaction_type="Meeting",
        date="2025-04-19",
        time="19:36",
        attendees=["Rep John", "Nurse Kelly"],
        topics_discussed="Discussed OncoBoost Phase III efficacy",
        outcomes="HCP receptive, wants brochures",
        follow_up_actions="Send brochures next week",
        observed_sentiment="Positive",
        materials_shared=["OncoBoost Phase III PDF"],
        samples_distributed=[{"name": "OncoBoost 10mg Starter Kit", "quantity": 2}]
    )
    
    log_data = json.loads(log_res)
    assert log_data["status"] == "success"
    int_id = log_data["interaction_id"]
    assert int_id > 0
    
    # Test editing that interaction
    edit_res = edit_interaction(
        interaction_id=int_id,
        updates={
            "topics_discussed": "Discussed OncoBoost efficacy and dosage guidelines",
            "observed_sentiment": "Positive"
        }
    )
    
    edit_data = json.loads(edit_res)
    assert edit_data["status"] == "success"
    
    # Verify in DB
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == int_id).first()
        assert interaction is not None
        assert interaction.topics_discussed == "Discussed OncoBoost efficacy and dosage guidelines"
    finally:
        db.close()

def test_langgraph_agent_extraction():
    initial_state = {
        "message": "Met Dr. Anita Sharma today. Discussed OncoBoost Phase III trials and she had positive sentiment.",
        "form_state": {
            "hcp_name": "",
            "hcp_id": None,
            "type": "Meeting",
            "date": "",
            "time": "",
            "attendees": [],
            "topics_discussed": "",
            "outcomes": "",
            "follow_up_actions": "",
            "observed_sentiment": "Neutral",
            "materials": [],
            "samples": []
        },
        "reply": "",
        "suggestions": [],
        "logged": False,
        "logged_id": None
    }
    
    res = agent_graph.invoke(initial_state)
    assert res["form_state"]["hcp_name"] == "Dr. Anita Sharma"
    assert res["form_state"]["hcp_id"] == 1
    assert "OncoBoost Phase III PDF" in res["form_state"]["materials"]
    assert res["form_state"]["observed_sentiment"] == "Positive"
    assert len(res["suggestions"]) > 0

def test_fastapi_endpoints():
    client = TestClient(app)
    
    # Test metadata routes
    res = client.get("/api/hcps")
    assert res.status_code == 200
    assert len(res.json()) >= 4
    
    res = client.get("/api/materials")
    assert res.status_code == 200
    assert len(res.json()) >= 4
    
    res = client.get("/api/samples")
    assert res.status_code == 200
    assert len(res.json()) >= 3
    
    # Test chat route
    chat_payload = {
        "message": "Met Dr. Vikram Patel. Sentiment was neutral.",
        "current_state": {
            "hcp_name": "",
            "hcp_id": None,
            "type": "Meeting",
            "date": "2025-04-19",
            "time": "19:36",
            "attendees": [],
            "topics_discussed": "",
            "outcomes": "",
            "follow_up_actions": "",
            "observed_sentiment": "Neutral",
            "materials": [],
            "samples": []
        },
        "session_id": "test-session"
    }
    
    res = client.post("/api/chat", json=chat_payload)
    assert res.status_code == 200
    chat_data = res.json()
    assert chat_data["updated_state"]["hcp_name"] == "Dr. Vikram Patel"
    assert chat_data["updated_state"]["observed_sentiment"] == "Neutral"
    assert "reply" in chat_data
    assert "suggestions" in chat_data
