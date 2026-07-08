from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
import uvicorn

import database
from database import SessionLocal, HCP, Material, Sample, Interaction, InteractionSample, SuggestedFollowUp, init_db
from schemas import (
    ChatRequest, ChatResponse, InteractionCreate, InteractionResponse,
    HCPResponse, MaterialResponse, SampleResponse, InteractionFormState
)
from agent import agent_graph

# Initialize database
init_db()

app = FastAPI(title="AI-First CRM HCP Module API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get db session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. Chat/AI Agent Assistant Endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat_assistant(req: ChatRequest):
    try:
        # Prepare LangGraph state
        initial_state = {
            "message": req.message,
            "form_state": req.current_state.model_dump(),
            "reply": "",
            "suggestions": [],
            "logged": False,
            "logged_id": None
        }
        
        # Execute LangGraph Compiled Graph
        res = agent_graph.invoke(initial_state)
        
        return ChatResponse(
            reply=res["reply"],
            updated_state=InteractionFormState(**res["form_state"]),
            suggestions=res["suggestions"],
            logged=res["logged"],
            logged_id=res["logged_id"]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"LangGraph Agent Error: {str(e)}"
        )

# 2. Get autocomplete lists
@app.get("/api/hcps", response_model=List[HCPResponse])
def get_hcps(db: Session = Depends(get_db)):
    return db.query(HCP).all()

@app.get("/api/materials", response_model=List[MaterialResponse])
def get_materials(db: Session = Depends(get_db)):
    return db.query(Material).all()

@app.get("/api/samples", response_model=List[SampleResponse])
def get_samples(db: Session = Depends(get_db)):
    return db.query(Sample).all()

# 3. Create interaction (Manual Log)
@app.post("/api/interactions", response_model=InteractionResponse)
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    try:
        # Create core interaction
        interaction = Interaction(
            hcp_id=payload.hcp_id,
            type=payload.type,
            date=payload.date,
            time=payload.time,
            attendees=", ".join(payload.attendees) if payload.attendees else "",
            topics_discussed=payload.topics_discussed,
            outcomes=payload.outcomes,
            follow_up_actions=payload.follow_up_actions,
            observed_sentiment=payload.observed_sentiment
        )
        db.add(interaction)
        db.flush() # get ID

        # Map materials
        if payload.materials:
            mats = db.query(Material).filter(Material.id.in_(payload.materials)).all()
            interaction.materials = mats

        # Map samples and decrement stock
        if payload.samples:
            for s_input in payload.samples:
                sample_obj = db.query(Sample).filter(Sample.id == s_input.sample_id).first()
                if sample_obj:
                    # check stock
                    qty = s_input.quantity
                    if sample_obj.stock >= qty:
                        sample_obj.stock -= qty
                    else:
                        qty = sample_obj.stock
                        sample_obj.stock = 0
                        
                    int_sample = InteractionSample(
                        interaction_id=interaction.id,
                        sample_id=sample_obj.id,
                        quantity=qty
                    )
                    db.add(int_sample)
                    
        # Generate follow-up suggestions using rules/LLM logic
        import tools
        sugs_str = tools.generate_followups(payload.topics_discussed or "", payload.outcomes or "")
        import json
        sugs = json.loads(sugs_str)
        for s_text in sugs:
            db.add(SuggestedFollowUp(interaction_id=interaction.id, suggestion_text=s_text))
            
        db.commit()
        db.refresh(interaction)
        
        # Prepare response model manually to map relationships correctly
        return map_interaction_to_response(interaction, db)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save interaction: {str(e)}"
        )

# 4. Edit interaction (Manual edit)
@app.put("/api/interactions/{id}")
def update_interaction(id: int, payload: InteractionCreate, db: Session = Depends(get_db)):
    interaction = db.query(Interaction).filter(Interaction.id == id).first()
    if not interaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Interaction ID {id} not found")
        
    try:
        interaction.hcp_id = payload.hcp_id
        interaction.type = payload.type
        interaction.date = payload.date
        interaction.time = payload.time
        interaction.attendees = ", ".join(payload.attendees) if payload.attendees else ""
        interaction.topics_discussed = payload.topics_discussed
        interaction.outcomes = payload.outcomes
        interaction.follow_up_actions = payload.follow_up_actions
        interaction.observed_sentiment = payload.observed_sentiment
        
        # Update materials
        interaction.materials = []
        if payload.materials:
            mats = db.query(Material).filter(Material.id.in_(payload.materials)).all()
            interaction.materials = mats
            
        # Update samples (stock adjust is omitted for simplicity in manual edit edit, or we can restore stock and re-apply)
        db.query(InteractionSample).filter(InteractionSample.interaction_id == id).delete()
        if payload.samples:
            for s_input in payload.samples:
                int_sample = InteractionSample(
                    interaction_id=id,
                    sample_id=s_input.sample_id,
                    quantity=s_input.quantity
                )
                db.add(int_sample)
                
        db.commit()
        return {"status": "success", "message": f"Interaction {id} updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update interaction: {str(e)}"
        )

# 5. List interactions
@app.get("/api/interactions", response_model=List[InteractionResponse])
def list_interactions(db: Session = Depends(get_db)):
    interactions = db.query(Interaction).order_by(Interaction.id.desc()).all()
    res = []
    for item in interactions:
        res.append(map_interaction_to_response(item, db))
    return res

def map_interaction_to_response(item: Interaction, db: Session) -> dict:
    # Manual mapping to align Pydantic structure
    mats_mapped = [{"id": m.id, "name": m.name, "type": m.type} for m in item.materials]
    
    samples_mapped = []
    int_samples = db.query(InteractionSample).filter(InteractionSample.interaction_id == item.id).all()
    for isamp in int_samples:
        samples_mapped.append({
            "sample": {
                "id": isamp.sample.id,
                "name": isamp.sample.name,
                "stock": isamp.sample.stock
            },
            "quantity": isamp.quantity
        })
        
    sugs_mapped = [s.suggestion_text for s in item.suggested_followups]
    
    hcp_mapped = None
    if item.hcp:
        hcp_mapped = {
            "id": item.hcp.id,
            "name": item.hcp.name,
            "specialty": item.hcp.specialty,
            "clinic": item.hcp.clinic,
            "email": item.hcp.email,
            "phone": item.hcp.phone
        }
        
    return {
        "id": item.id,
        "hcp_id": item.hcp_id,
        "hcp": hcp_mapped,
        "type": item.type,
        "date": item.date,
        "time": item.time,
        "attendees": [a.strip() for a in item.attendees.split(",") if a.strip()] if item.attendees else [],
        "topics_discussed": item.topics_discussed,
        "outcomes": item.outcomes,
        "follow_up_actions": item.follow_up_actions,
        "observed_sentiment": item.observed_sentiment,
        "materials": mats_mapped,
        "samples": samples_mapped,
        "suggested_followups": sugs_mapped
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
