# AI-First CRM HCP Module – Log Interaction Screen

This project is a Customer Relationship Management (CRM) prototype specifically tailored for life science representatives to log healthcare professional (HCP) interactions. It features a modern, dual-mode interface offering reps the flexibility to log interactions using either a **Structured Form** or a **Conversational Chat Interface** powered by an AI Agent.

---

## 🌟 Key Features

1. **Structured Form Interface**:
   - Autocomplete search and select for Healthcare Professionals (HCPs) from the database.
   - Automatic suggestions of scientific materials ("OncoBoost Phase III PDF") and sample catalog tracking.
   - Emoji-based sentiment inputs (Positive, Neutral, Negative).
   - Direct database persistence.
2. **Conversational AI Assistant (LangGraph & LLM)**:
   - Powered by a LangGraph state machine.
   - Seamlessly extracts entities (HCP names, materials, samples, sentiment, date/time, discussion topics) from conversational inputs.
   - Automatically synchronizes extracted data back into the left form input fields in real time.
3. **Voice Summarization Mock**:
   - Reps can simulate speaking voice notes. The application transcribes, parses entities, and updates the form values automatically using the LangGraph agent.
4. **Relational Database Logs**:
   - Seeded SQLite database storing doctors, materials, sample inventories, and historical logs.
   - Real-time tabular logs display at the bottom of the interface to visually confirm database operations.
5. **Aesthetics & Design**:
   - Sleek dark theme dashboard layout with glassmorphic cards and linear purple/indigo gradient accents.
   - Typography centered around Google Inter font.

---

## 🛠️ Technology Stack

- **Frontend**: React (Vite), Redux Toolkit (State Management), Lucide Icons, Vanilla CSS.
- **Backend**: Python 3.x, FastAPI (Web framework), SQLAlchemy (relational database ORM).
- **AI Agent Framework**: LangGraph, LangChain Core.
- **LLM Provider**: Groq API (`gemma2-9b-it` or `llama-3.3-70b-versatile`).
- **Database**: Relational SQLite (`crm.db`) out-of-the-box, configurable via environment variable for PostgreSQL or MySQL.

---

## 📂 Project Structure

```
assignment/
├── backend/
│   ├── .env                  # Backend configuration & Groq API keys
│   ├── agent.py              # LangGraph state machine & AI extraction flow
│   ├── database.py           # SQLAlchemy database model definitions & seed script
│   ├── main.py               # FastAPI server and endpoints
│   ├── requirements.txt      # Python dependencies
│   ├── schemas.py            # Pydantic request/response validation schemas
│   ├── test_backend.py       # Programmatic Pytest test suite
│   └── tools.py              # The 5 specialized LangGraph agent tools
└── frontend/
    ├── index.html            # Vite HTML template
    ├── package.json          # Node dependencies
    └── src/
        ├── App.jsx           # Main React component (Split view Form + Chat)
        ├── index.css         # Custom responsive design styles
        ├── main.jsx          # React entrypoint
        └── store.js          # Redux Toolkit configuration & API thunks
```

---

## ⚙️ Setup and Installation

### 1. Prerequisites
- **Node.js** (v18+)
- **Python** (v3.10+)

### 2. Backend Installation & Run
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. *(Optional)* Set your Groq API Key:
   Open the `backend/.env` file and replace the `GROQ_API_KEY` placeholder:
   ```env
   GROQ_API_KEY=gsk_your_actual_groq_api_token
   ```
   *Note: If no Groq API Key is configured, the application falls back to a local regex-based pattern matching extractor, allowing you to fully test the interface, automatic form-filling, tool execution, and database logging offline.*
4. Initialize the database with seed data:
   ```bash
   python database.py
   ```
5. Start the FastAPI development server:
   ```bash
   python -m uvicorn main:app --reload --port 8000
   ```
   The backend API will run at `http://127.0.0.1:8000`.

### 3. Frontend Installation & Run
1. Open a new terminal tab and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Vite React development server:
   ```bash
   npm run dev
   ```
   Open your browser and navigate to the printed URL (typically `http://localhost:5173`).

---

## 🤖 LangGraph Agent & Tools

The backend features a LangGraph agent that controls the interaction logging cycle. It uses 5 specific tools for managing actions:

1. **`log_interaction`** (Required): Captures the extracted parameters (HCP ID, Date, Time, Topics, Sentiment, Materials, Samples), resolves relationship mapping, decrements sample stock, saves the record to the SQL database, and generates follow-ups.
2. **`edit_interaction`** (Required): Allows modification of previously logged records by updating their database fields based on the interaction ID.
3. **`search_hcp`**: Queries the database using name or specialty keywords to resolve matching HCP records.
4. **`search_materials_and_samples`**: Searches catalog collections to locate marketing brochures or starter pack inventories.
5. **`generate_followups`**: Scans meeting discussion items and dynamically generates follow-up tasks (e.g. scheduling calls or sending specific scientific papers).

---

## 🧪 Running Automated Tests

We provide a robust suite of unit and integration tests. To run them, execute:
```bash
cd backend
python -m pytest test_backend.py
```
This tests database seeding, individual tools, the LangGraph extraction logic, and FastAPI endpoints.
