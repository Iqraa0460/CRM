from pydantic import BaseModel, Field
from typing import List, Optional

class HCPBase(BaseModel):
    name: str
    specialty: str
    clinic: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class HCPResponse(HCPBase):
    id: int
    class Config:
        from_attributes = True

class MaterialResponse(BaseModel):
    id: int
    name: str
    type: str
    class Config:
        from_attributes = True

class SampleResponse(BaseModel):
    id: int
    name: str
    stock: int
    class Config:
        from_attributes = True

class InteractionSampleInput(BaseModel):
    sample_id: int
    quantity: int

class InteractionSampleResponse(BaseModel):
    sample: SampleResponse
    quantity: int
    class Config:
        from_attributes = True

class InteractionCreate(BaseModel):
    hcp_id: Optional[int] = None
    type: str = "Meeting"
    date: str
    time: str
    attendees: Optional[List[str]] = []
    topics_discussed: Optional[str] = ""
    outcomes: Optional[str] = ""
    follow_up_actions: Optional[str] = ""
    observed_sentiment: str = "Neutral"
    materials: Optional[List[int]] = [] # IDs of materials
    samples: Optional[List[InteractionSampleInput]] = [] # List of sample IDs and quantities

class InteractionResponse(BaseModel):
    id: int
    hcp_id: Optional[int] = None
    hcp: Optional[HCPResponse] = None
    type: str
    date: str
    time: str
    attendees: Optional[List[str]] = []
    topics_discussed: Optional[str] = ""
    outcomes: Optional[str] = ""
    follow_up_actions: Optional[str] = ""
    observed_sentiment: str
    materials: List[MaterialResponse] = []
    samples: List[InteractionSampleResponse] = []
    suggested_followups: List[str] = []

    class Config:
        from_attributes = True

# Chat Schemas
class InteractionFormState(BaseModel):
    hcp_name: Optional[str] = None
    hcp_id: Optional[int] = None
    type: Optional[str] = "Meeting"
    date: Optional[str] = None
    time: Optional[str] = None
    attendees: Optional[List[str]] = []
    topics_discussed: Optional[str] = ""
    outcomes: Optional[str] = ""
    follow_up_actions: Optional[str] = ""
    observed_sentiment: Optional[str] = "Neutral"
    materials: Optional[List[str]] = [] # Material names
    samples: Optional[List[dict]] = [] # e.g. [{"name": "OncoBoost 10mg", "quantity": 2}]

class ChatRequest(BaseModel):
    message: str
    current_state: InteractionFormState
    session_id: str

class ChatResponse(BaseModel):
    reply: str
    updated_state: InteractionFormState
    suggestions: List[str]
    logged: bool = False
    logged_id: Optional[int] = None
