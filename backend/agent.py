import os
import json
import re
from datetime import datetime
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from tools import log_interaction, edit_interaction, search_hcp, search_materials_and_samples, generate_followups

# Attempt to import langchain/groq
try:
    from langchain_groq import ChatGroq
    from langchain_core.messages import SystemMessage, HumanMessage
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

class AgentState(TypedDict):
    message: str
    form_state: dict
    reply: str
    suggestions: List[str]
    logged: bool
    logged_id: Optional[int]

def mock_extract_entities(message: str, current_state: dict) -> tuple[dict, str]:
    """
    Fallback regex-based entity extractor to mimic LLM behavior when Groq is not available.
    """
    updated = dict(current_state)
    
    # 1. Resolve HCP
    if re.search(r"sharma|anita", message, re.IGNORECASE):
        updated["hcp_name"] = "Dr. Anita Sharma"
        updated["hcp_id"] = 1
    elif re.search(r"patel|vikram", message, re.IGNORECASE):
        updated["hcp_name"] = "Dr. Vikram Patel"
        updated["hcp_id"] = 2
    elif re.search(r"jenkins|sarah", message, re.IGNORECASE):
        updated["hcp_name"] = "Dr. Sarah Jenkins"
        updated["hcp_id"] = 3
    elif re.search(r"kim|david", message, re.IGNORECASE):
        updated["hcp_name"] = "Dr. David Kim"
        updated["hcp_id"] = 4
        
    # 2. Resolve Interaction Type
    if re.search(r"\bcall\b|\bphone\b", message, re.IGNORECASE):
        updated["type"] = "Call"
    elif re.search(r"\bemail\b|\bemailed\b", message, re.IGNORECASE):
        updated["type"] = "Email"
    elif re.search(r"\bmeeting\b|\bmet\b", message, re.IGNORECASE):
        updated["type"] = "Meeting"
        
    # 3. Resolve Date & Time
    if "today" in message.lower():
        updated["date"] = datetime.now().strftime("%Y-%m-%d")
    elif "yesterday" in message.lower():
        # simple mock
        updated["date"] = "2025-04-18"
    elif not updated.get("date"):
        updated["date"] = "2025-04-19"
        
    if not updated.get("time"):
        updated["time"] = datetime.now().strftime("%H:%M")
        
    # 4. Attendees
    attendee_matches = re.findall(r"(?:with|attendees:)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", message)
    if attendee_matches:
        for att in attendee_matches:
            if "Dr." not in att and att not in updated.get("attendees", []):
                updated["attendees"] = list(set((updated.get("attendees") or []) + [att]))

    # 5. Topics
    topics_match = re.search(r"(?:discuss|discussed|topics?)\s+(.*?)(?:\.|outcome|sentiment|samples?|materials?|$)", message, re.IGNORECASE)
    if topics_match:
        updated["topics_discussed"] = topics_match.group(1).strip()
        
    # 6. Outcomes
    outcomes_match = re.search(r"(?:outcome|agreed|decided)\s+(.*?)(?:\.|sentiment|samples?|materials?|$)", message, re.IGNORECASE)
    if outcomes_match:
        updated["outcomes"] = outcomes_match.group(1).strip()

    # 7. Follow-ups
    followup_match = re.search(r"(?:follow-up|followup|next steps?)\s+(.*?)(?:\.|sentiment|samples?|materials?|$)", message, re.IGNORECASE)
    if followup_match:
        updated["follow_up_actions"] = followup_match.group(1).strip()
        
    # 8. Sentiment
    if re.search(r"positive|happy|glad|interested|receptive", message, re.IGNORECASE):
        updated["observed_sentiment"] = "Positive"
    elif re.search(r"negative|refused|unhappy|disliked", message, re.IGNORECASE):
        updated["observed_sentiment"] = "Negative"
    elif re.search(r"neutral|ok|okay|fine", message, re.IGNORECASE):
        updated["observed_sentiment"] = "Neutral"

    # 9. Materials & Samples
    materials = updated.get("materials") or []
    samples = updated.get("samples") or []
    
    if "oncoboost" in message.lower():
        if "brochure" in message.lower():
            if "OncoBoost Brochure" not in materials:
                materials.append("OncoBoost Brochure")
        else:
            if "OncoBoost Phase III PDF" not in materials:
                materials.append("OncoBoost Phase III PDF")
        
        if "sample" in message.lower() or "kit" in message.lower() or "starter" in message.lower():
            # Check quantity
            qty_match = re.search(r"(\d+)\s+(?:sample|kit|starter)", message, re.IGNORECASE)
            qty = int(qty_match.group(1)) if qty_match else 1
            samples.append({"name": "OncoBoost 10mg Starter Kit", "quantity": qty})
            
    if "cardiashield" in message.lower():
        if "slides" in message.lower() or "efficacy" in message.lower():
            if "CardiaShield Efficacy Slides" not in materials:
                materials.append("CardiaShield Efficacy Slides")
        if "sample" in message.lower() or "pack" in message.lower():
            qty_match = re.search(r"(\d+)\s+(?:sample|pack)", message, re.IGNORECASE)
            qty = int(qty_match.group(1)) if qty_match else 1
            samples.append({"name": "CardiaShield 5mg Trial Packs", "quantity": qty})
            
    if "neuroflow" in message.lower():
        if "sheet" in message.lower() or "product" in message.lower():
            if "NeuroFlow Product Sheet" not in materials:
                materials.append("NeuroFlow Product Sheet")
        if "sample" in message.lower():
            qty_match = re.search(r"(\d+)\s+(?:sample)", message, re.IGNORECASE)
            qty = int(qty_match.group(1)) if qty_match else 1
            samples.append({"name": "NeuroFlow 20mg Samples", "quantity": qty})

    updated["materials"] = list(set(materials))
    # Deduplicate samples by name
    dedup_samples = {}
    for s in samples:
        dedup_samples[s["name"]] = dedup_samples.get(s["name"], 0) + s["quantity"]
    updated["samples"] = [{"name": name, "quantity": qty} for name, qty in dedup_samples.items()]

    # Generate reply
    reply = "I've extracted the interaction details and updated the form. "
    updates = []
    if updated.get("hcp_name") != current_state.get("hcp_name"):
        updates.append(f"HCP: {updated['hcp_name']}")
    if updated.get("type") != current_state.get("type"):
        updates.append(f"Type: {updated['type']}")
    if updated.get("topics_discussed") != current_state.get("topics_discussed"):
        updates.append("Topics Discussed")
    if updated.get("observed_sentiment") != current_state.get("observed_sentiment"):
        updates.append(f"Sentiment: {updated['observed_sentiment']}")
    if len(updated.get("materials", [])) > len(current_state.get("materials", [])):
        updates.append("Materials Shared")
    if len(updated.get("samples", [])) > len(current_state.get("samples", [])):
        updates.append("Samples Distributed")
        
    if updates:
        reply += f"Updated fields: {', '.join(updates)}."
    else:
        reply += "No new fields were identified. Could you provide details on topics discussed, outcomes, or products shared?"
        
    return updated, reply

def extractor_node(state: AgentState) -> dict:
    """
    Main node that updates interaction details from human conversational text.
    If the user asks to save/log or update an ID, this node prepares tool execution.
    """
    message = state["message"]
    form_state = state["form_state"]
    groq_api_key = os.getenv("GROQ_API_KEY")
    
    logged = False
    logged_id = None
    reply = ""
    updated_state = dict(form_state)
    
    # Check if this is an explicit command to LOG or SAVE
    is_log_command = any(word in message.lower() for word in ["log this", "save this", "save the meeting", "submit interaction", "finalize log", "save interaction", "log it", "done"])
    
    # Check if this is an edit command
    is_edit_command = re.search(r"edit\s+(?:interaction\s+)?(\d+)|update\s+(?:interaction\s+)?(\d+)", message, re.IGNORECASE)
    
    if is_log_command:
        # Trigger the log_interaction tool
        hcp_name = form_state.get("hcp_name") or "Unknown HCP"
        if not hcp_name or hcp_name == "Unknown HCP":
            # Scan message for potential HCP name to save
            mock_temp, _ = mock_extract_entities(message, form_state)
            hcp_name = mock_temp.get("hcp_name") or "Unknown HCP"
            updated_state["hcp_name"] = hcp_name
            
        res_str = log_interaction(
            hcp_name=hcp_name,
            interaction_type=form_state.get("type", "Meeting"),
            date=form_state.get("date"),
            time=form_state.get("time"),
            attendees=form_state.get("attendees", []),
            topics_discussed=form_state.get("topics_discussed", ""),
            outcomes=form_state.get("outcomes", ""),
            follow_up_actions=form_state.get("follow_up_actions", ""),
            observed_sentiment=form_state.get("observed_sentiment", "Neutral"),
            materials_shared=form_state.get("materials", []),
            samples_distributed=form_state.get("samples", [])
        )
        
        try:
            res = json.loads(res_str)
            if res.get("status") == "success":
                logged = True
                logged_id = res.get("interaction_id")
                reply = f"Successfully logged the interaction with {hcp_name} in the database (ID: {logged_id})."
            else:
                reply = f"Failed to log interaction: {res.get('message')}"
        except Exception as e:
            reply = f"Logged but failed to parse DB response: {e}"
            
    elif is_edit_command:
        int_id = int(is_edit_command.group(1) or is_edit_command.group(2))
        # Perform extraction on updates
        extracted, _ = mock_extract_entities(message, form_state)
        # Prepare updates payload
        updates_payload = {}
        for k in ["type", "date", "time", "topics_discussed", "outcomes", "follow_up_actions", "observed_sentiment", "materials", "samples"]:
            if extracted.get(k) != form_state.get(k):
                updates_payload[k] = extracted[k]
                
        if not updates_payload:
            # Fallback: update whatever is in form_state
            updates_payload = {
                "topics_discussed": form_state.get("topics_discussed"),
                "outcomes": form_state.get("outcomes"),
                "follow_up_actions": form_state.get("follow_up_actions"),
                "observed_sentiment": form_state.get("observed_sentiment")
            }
            
        res_str = edit_interaction(interaction_id=int_id, updates=updates_payload)
        try:
            res = json.loads(res_str)
            if res.get("status") == "success":
                reply = f"Successfully updated Interaction ID {int_id} with the latest information."
            else:
                reply = f"Failed to edit interaction: {res.get('message')}"
        except Exception as e:
            reply = f"Updated but failed to parse response: {e}"
            
    else:
        # Regular conversational extraction
        if HAS_LANGCHAIN and groq_api_key:
            try:
                llm = ChatGroq(model_name="gemma2-9b-it", groq_api_key=groq_api_key, temperature=0.1)
                
                # Format system instructions
                prompt = (
                    "You are an AI-CRM digital assistant helping a life sciences representative. "
                    "Analyze the user's message and current form state to extract interaction metadata.\n"
                    f"Current Form State: {json.dumps(form_state)}\n"
                    f"User Message: \"{message}\"\n\n"
                    "Extract the following properties in JSON format:\n"
                    "- hcp_name (Dr. Anita Sharma, Dr. Vikram Patel, Dr. Sarah Jenkins, Dr. David Kim)\n"
                    "- type (Meeting, Call, Email, Presentation)\n"
                    "- date (YYYY-MM-DD)\n"
                    "- time (HH:MM)\n"
                    "- attendees (array of names)\n"
                    "- topics_discussed (brief string summary of science topics)\n"
                    "- outcomes (decisions/actions)\n"
                    "- follow_up_actions (next tasks)\n"
                    "- observed_sentiment (Positive, Neutral, Negative)\n"
                    "- materials (array of material names: OncoBoost Phase III PDF, OncoBoost Brochure, CardiaShield Efficacy Slides, NeuroFlow Product Sheet)\n"
                    "- samples (array of objects: {name: str, quantity: int})\n\n"
                    "Return a JSON object with two fields:\n"
                    "1. 'reply': A summary conversation response acknowledging what you extracted.\n"
                    "2. 'extracted': The updated form state values merging the new details into the current state.\n"
                    "Ensure your entire output is valid JSON only."
                )
                
                response = llm.invoke([HumanMessage(content=prompt)])
                response_content = response.content.strip()
                
                # Extract JSON from block if formatted as ```json
                if "```" in response_content:
                    json_match = re.search(r"```json\s*(.*?)\s*```", response_content, re.DOTALL)
                    if json_match:
                        response_content = json_match.group(1)
                    else:
                        response_content = re.sub(r"```[a-zA-Z]*|```", "", response_content)
                        
                parsed = json.loads(response_content)
                reply = parsed.get("reply", "Form details updated.")
                extracted_data = parsed.get("extracted", {})
                
                # Merge fields safely
                for k, v in extracted_data.items():
                    if v is not None and v != "" and v != []:
                        updated_state[k] = v
            except Exception as ex:
                print(f"Groq LLM exception, falling back to mock: {ex}")
                updated_state, reply = mock_extract_entities(message, form_state)
        else:
            # Run Mock regex extractor
            updated_state, reply = mock_extract_entities(message, form_state)

    # 10. Generate follow-up suggestions dynamically
    suggestions_json = generate_followups(
        updated_state.get("topics_discussed", ""),
        updated_state.get("outcomes", "")
    )
    suggestions = json.loads(suggestions_json)
    
    return {
        "message": message,
        "form_state": updated_state,
        "reply": reply,
        "suggestions": suggestions,
        "logged": logged,
        "logged_id": logged_id
    }

# Building LangGraph Workflow Graph
workflow = StateGraph(AgentState)

# Add node
workflow.add_node("extractor", extractor_node)

# Set Entry Point
workflow.set_entry_point("extractor")

# Add edge to END
workflow.add_edge("extractor", END)

# Compile graph
agent_graph = workflow.compile()
