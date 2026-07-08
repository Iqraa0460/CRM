import json
from datetime import datetime
from sqlalchemy.orm import Session
from database import SessionLocal, HCP, Material, Sample, Interaction, InteractionSample, SuggestedFollowUp, init_db

# Ensure DB is initialized
init_db()

def search_hcp(query: str) -> str:
    """
    Search for Healthcare Professionals (HCPs) in the database by name or specialty.
    Args:
        query: Name or specialty of the HCP (e.g. 'Sharma' or 'Oncology')
    Returns:
        A list of matching HCP records.
    """
    db = SessionLocal()
    try:
        results = db.query(HCP).filter(
            (HCP.name.ilike(f"%{query}%")) | (HCP.specialty.ilike(f"%{query}%"))
        ).all()
        
        if not results:
            return f"No HCPs found matching '{query}'."
        
        output = []
        for h in results:
            output.append({
                "id": h.id,
                "name": h.name,
                "specialty": h.specialty,
                "clinic": h.clinic,
                "email": h.email
            })
        return json.dumps(output, indent=2)
    finally:
        db.close()

def search_materials_and_samples(query: str) -> str:
    """
    Search for scientific materials or drug samples in the catalog.
    Args:
        query: Name of material/sample (e.g. 'OncoBoost')
    Returns:
        Catalog items including stock levels for samples.
    """
    db = SessionLocal()
    try:
        materials = db.query(Material).filter(Material.name.ilike(f"%{query}%")).all()
        samples = db.query(Sample).filter(Sample.name.ilike(f"%{query}%")).all()
        
        output = {
            "materials": [{"id": m.id, "name": m.name, "type": m.type} for m in materials],
            "samples": [{"id": s.id, "name": s.name, "stock": s.stock} for s in samples]
        }
        return json.dumps(output, indent=2)
    finally:
        db.close()

def generate_followups(topics_discussed: str, outcomes: str) -> str:
    """
    Generate AI suggested follow-ups for life science sales reps based on meeting topics and outcomes.
    Args:
        topics_discussed: Brief outline of the topics (e.g. 'Discussed efficacy and clinical trials')
        outcomes: Meeting outcomes (e.g. 'HCP interested in starter kits')
    Returns:
        List of suggested follow-up actions.
    """
    # Simulate an expert life science clinical recommender system.
    # In a full setup, this could prompt the LLM, but we can combine rule-based & LLM heuristics.
    suggestions = []
    text = f"{topics_discussed} {outcomes}".lower()
    
    if "oncoboost" in text or "oncology" in text or "cancer" in text:
        suggestions.append("Send OncoBoost Phase III PDF")
        suggestions.append("Add Dr. Sharma to advisory board invite list")
    if "cardiashield" in text or "cardio" in text or "heart" in text:
        suggestions.append("Share CardiaShield Efficacy Slide Deck")
        suggestions.append("Send CardiaShield 5mg Trial Packs to Clinic")
    if "neuroflow" in text or "neuro" in text or "brain" in text:
        suggestions.append("Send NeuroFlow Product Sheet")
        suggestions.append("Schedule follow-up discussion on NeuroFlow dosage")
    
    # Generic suggestions
    suggestions.append("Schedule follow-up meeting in 2 weeks")
    suggestions.append("Log call outcomes in CRM portal")
    
    return json.dumps(list(set(suggestions))[:3], indent=2)

def log_interaction(
    hcp_name: str,
    interaction_type: str,
    date: str,
    time: str,
    attendees: list = None,
    topics_discussed: str = "",
    outcomes: str = "",
    follow_up_actions: str = "",
    observed_sentiment: str = "Neutral",
    materials_shared: list = None, # List of material names or IDs
    samples_distributed: list = None # List of dicts: [{"name": str, "quantity": int}] or [{"sample_id": int, "quantity": int}]
) -> str:
    """
    Saves a completed HCP interaction log to the database and schedules follow-up actions.
    All parameters are extracted by the LLM from the conversational log or passed from the form.
    Returns:
        JSON response with the logged interaction ID and details.
    """
    db = SessionLocal()
    try:
        # 1. Resolve HCP
        hcp = db.query(HCP).filter(HCP.name.ilike(f"%{hcp_name}%")).first()
        hcp_id = hcp.id if hcp else None
        
        # 2. Format Date/Time if not provided
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        if not time:
            time = datetime.now().strftime("%H:%M")
            
        # 3. Create Interaction
        interaction = Interaction(
            hcp_id=hcp_id,
            type=interaction_type or "Meeting",
            date=date,
            time=time,
            attendees=", ".join(attendees) if attendees else "",
            topics_discussed=topics_discussed,
            outcomes=outcomes,
            follow_up_actions=follow_up_actions,
            observed_sentiment=observed_sentiment or "Neutral"
        )
        
        db.add(interaction)
        db.flush() # Get interaction.id
        
        # 4. Process Materials
        if materials_shared:
            for mat_name in materials_shared:
                mat = db.query(Material).filter(
                    (Material.name.ilike(f"%{mat_name}%")) | (Material.id == (int(mat_name) if isinstance(mat_name, int) or mat_name.isdigit() else -1))
                ).first()
                if mat:
                    interaction.materials.append(mat)
                    
        # 5. Process Samples
        if samples_distributed:
            for s_info in samples_distributed:
                s_name = s_info.get("name", "")
                s_id = s_info.get("sample_id", None)
                qty = s_info.get("quantity", 1)
                
                sample_obj = None
                if s_id:
                    sample_obj = db.query(Sample).filter(Sample.id == s_id).first()
                elif s_name:
                    sample_obj = db.query(Sample).filter(Sample.name.ilike(f"%{s_name}%")).first()
                    
                if sample_obj:
                    # Check stock and decrement
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
        
        # 6. Generate Suggestions and store
        suggestions_json = generate_followups(topics_discussed, outcomes)
        suggestions = json.loads(suggestions_json)
        for sug in suggestions:
            db.add(SuggestedFollowUp(interaction_id=interaction.id, suggestion_text=sug))
            
        db.commit()
        
        # Construct summary response
        response = {
            "status": "success",
            "message": "Interaction logged successfully.",
            "interaction_id": interaction.id,
            "hcp_resolved": hcp.name if hcp else "Unknown (Pending identification)",
            "date": date,
            "time": time,
            "sentiment": observed_sentiment,
            "suggestions": suggestions
        }
        return json.dumps(response, indent=2)
        
    except Exception as e:
        db.rollback()
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()

def edit_interaction(
    interaction_id: int,
    updates: dict
) -> str:
    """
    Modifies an existing interaction log in the database.
    Args:
        interaction_id: ID of the interaction log to edit.
        updates: Dictionary of fields to update (e.g. {'topics_discussed': 'New topic', 'observed_sentiment': 'Positive'}).
    Returns:
        JSON response with the updated interaction info.
    """
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return json.dumps({"status": "error", "message": f"Interaction with ID {interaction_id} not found."})
            
        # Update scalar fields
        for field, val in updates.items():
            if hasattr(interaction, field) and field not in ['id', 'created_at', 'updated_at', 'materials', 'samples']:
                setattr(interaction, field, val)
                
        # Handle materials if provided
        if "materials" in updates:
            interaction.materials = []
            materials_list = updates["materials"]
            for mat_name in materials_list:
                mat = db.query(Material).filter(
                    (Material.name.ilike(f"%{mat_name}%")) | (Material.id == (int(mat_name) if isinstance(mat_name, int) or str(mat_name).isdigit() else -1))
                ).first()
                if mat:
                    interaction.materials.append(mat)
                    
        # Handle samples if provided
        if "samples" in updates:
            # Delete old sample relations
            db.query(InteractionSample).filter(InteractionSample.interaction_id == interaction_id).delete()
            samples_list = updates["samples"]
            for s_info in samples_list:
                s_name = s_info.get("name", "")
                s_id = s_info.get("sample_id", None)
                qty = s_info.get("quantity", 1)
                
                sample_obj = None
                if s_id:
                    sample_obj = db.query(Sample).filter(Sample.id == s_id).first()
                elif s_name:
                    sample_obj = db.query(Sample).filter(Sample.name.ilike(f"%{s_name}%")).first()
                    
                if sample_obj:
                    int_sample = InteractionSample(
                        interaction_id=interaction_id,
                        sample_id=sample_obj.id,
                        quantity=qty
                    )
                    db.add(int_sample)
                    
        db.commit()
        return json.dumps({
            "status": "success",
            "message": f"Interaction {interaction_id} updated successfully.",
            "interaction_id": interaction_id
        }, indent=2)
        
    except Exception as e:
        db.rollback()
        return json.dumps({"status": "error", "message": str(e)})
    finally:
        db.close()

# List of tool configurations for the LangGraph agent
tool_definitions = [
    {
        "name": "search_hcp",
        "description": "Search for Healthcare Professionals (HCPs) by name or specialty.",
        "func": search_hcp
    },
    {
        "name": "search_materials_and_samples",
        "description": "Search catalog for clinical materials and drug samples.",
        "func": search_materials_and_samples
    },
    {
        "name": "generate_followups",
        "description": "Generate suggested follow-up actions based on topics and outcomes.",
        "func": generate_followups
    },
    {
        "name": "log_interaction",
        "description": "Persist interaction log data to database.",
        "func": log_interaction
    },
    {
        "name": "edit_interaction",
        "description": "Modify existing interaction details in the database.",
        "func": edit_interaction
    }
]
