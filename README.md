# Founder Sidekick — API-First AI Agent Backend

**Founder Sidekick** is a production-grade, API-first AI agent designed as an intelligent companion for startup founders. It maintains context-aware conversations, retains long-term durable information across sessions, manages short-term conversational context, and executes persistent database operations using structured agent tools.

---

## 1. Project Overview

Startup founders need an AI companion that can remember critical long-term facts (such as product names, architecture decisions, and strategic goals) across different chat sessions, while also understanding immediate conversational context without wasting tokens or blowing up LLM prompt windows.

**Key Goals of the Assignment**:
* **Durable User Memory**: Persist long-term founder information separate from ordinary chat history.
* **Bounded Conversation Context**: Retain recent message history ($N$ turns) for conversational continuity without blindly sending unlimited past history.
* **Persistent Agent Tools**: Provide tools (`save_idea`, `get_idea`, `list_ideas`) operating on PostgreSQL data.
* **API-First Design**: Expose the agent via a clean REST API (`POST /chat`) documented with OpenAPI/Swagger.
* **Clean Engineering & Multi-User Isolation**: Maintain clean separation of concerns, robust transaction handling, and multi-user data scoping.

---

## 2. Features

* **Conversational Chat Interface**: Process multi-turn queries via REST API endpoints.
* **Bounded Conversation Context**: Configurable limit ($N=10$ by default) on recent message history.
* **Durable Founder Memory Architecture**: Long-term memory records (`memories` table) stored separately from short-term turn history (`messages` table).
* **Persistent Ideas Store**: Structured startup ideas saved and managed in PostgreSQL (`ideas` table).
* **Agno Agent Framework**: Agent orchestration layer handling tool registration and model execution.
* **Google Gemini 2.5 Flash**: Low-latency, cost-effective LLM provider via `google-genai`.
* **PostgreSQL / Supabase Persistence**: Relational storage managed with SQLAlchemy 2.x and versioned Alembic migrations.
* **Persistent Idea Tools**: Agent tools (`save_idea`, `get_idea`, `list_ideas`) for structured data operations.
* **User Data Isolation**: Strict user-level scoping on all database queries and tool actions.

---

## 3. Tech Stack

* **Language**: Python 3.11+
* **Framework**: FastAPI (Async REST API web framework)
* **Agent Framework**: Agno (`2.9.0`)
* **LLM Provider**: Google Gemini 2.5 Flash (`google-genai 2.19.0`)
* **ORM**: SQLAlchemy 2.x (Declarative Mapped models)
* **Database**: PostgreSQL (Supabase Hosted PostgreSQL)
* **Migrations**: Alembic (`1.19.1`)
* **Data Validation**: Pydantic v2
* **Testing**: Python `unittest` test suite

---

## 4. Architecture & Request Flow

### Request Flow Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Founder as Founder / Client
    participant API as FastAPI (POST /chat)
    participant Context as ContextManager
    participant Agent as Agno Agent Layer
    participant Gemini as Google Gemini 2.5 Flash
    participant Tools as Idea Tools
    participant Services as Application Services
    participant DB as Supabase PostgreSQL

    Founder->>API: POST /chat {user_id, conversation_id, message}
    API->>Services: Ensure User & Conversation exist
    Services->>DB: Upsert User / Conversation
    API->>Context: build_context(user_id, conversation_id, limit=10)
    Context->>Services: Fetch summary, recent messages, durable memories
    Services->>DB: Query DB
    DB-->>Context: Return DB models
    Context-->>API: Structured Context Payload
    API->>Services: MessageService.create_message(role="user")
    Services->>DB: Insert User Message
    API->>Agent: run_agent_turn(context, user_message)
    Agent->>Gemini: Prompt + Tools Registration
    opt Tool Execution
        Gemini-->>Agent: Call Tool (save_idea / get_idea / list_ideas)
        Agent->>Tools: Execute bound tool function
        Tools->>Services: IdeaService DB operations
        Services->>DB: Query / Insert Idea
        DB-->>Tools: Return Idea record
        Tools-->>Agent: Tool Response JSON
        Agent->>Gemini: Send Tool Result
    end
    Gemini-->>Agent: Final Response Text
    API->>Services: MessageService.create_message(role="assistant")
    Services->>DB: Insert Assistant Message
    API-->>Founder: ChatResponse {user_id, conversation_id, response}
```

---

## 5. Project Structure

```
founder-sidekick/
├── backend/
│   ├── alembic/
│   │   ├── env.py                  # Alembic environment config with dynamic DATABASE_URL
│   │   └── versions/
│   │       └── 001_initial_schema.py # Initial database migration script
│   ├── app/
│   │   ├── api/
│   │   │   └── chat.py             # POST /chat REST endpoint handler
│   │   ├── agent/
│   │   │   └── sidekick_agent.py   # Agno Agent setup & turn runner with Gemini
│   │   ├── context/
│   │   │   └── context_manager.py  # Bounded prompt context builder
│   │   ├── database/
│   │   │   ├── connection.py       # SQLAlchemy engine, session maker, get_db dependency
│   │   │   └── models.py           # SQLAlchemy 2.x ORM models (User, Conversation, Message, Memory, Idea)
│   │   ├── schemas/
│   │   │   └── chat.py             # Pydantic schemas (ChatRequest, ChatResponse)
│   │   ├── services/               # Application service layer (CRUD business logic)
│   │   │   ├── user_service.py
│   │   │   ├── conversation_service.py
│   │   │   ├── message_service.py
│   │   │   ├── memory_service.py
│   │   │   └── idea_service.py
│   │   ├── tools/
│   │   │   └── idea_tools.py       # Persistent PostgreSQL idea tools for agent
│   │   └── main.py                 # FastAPI app entry point & router registration
│   ├── tests/                      # Automated unit test suite (31 tests)
│   │   ├── test_services.py
│   │   ├── test_context_manager.py
│   │   ├── test_idea_tools.py
│   │   ├── test_agent.py
│   │   └── test_api.py
│   ├── .env.example
│   ├── alembic.ini
│   └── requirements.txt
└── README.md
```

---

## 6. Database Architecture

The PostgreSQL database contains 5 core relational entities defined in [`app/database/models.py`](file:///d:/REACT/founder-sidekick/backend/app/database/models.py):

| Table | Primary Key | Foreign Keys | Description |
| :--- | :--- | :--- | :--- |
| `users` | `id` (String) | None | Top-level founder/user entity. |
| `conversations` | `id` (String UUID) | `user_id` -> `users.id` (`CASCADE`) | Individual chat sessions with optional `summary`. |
| `messages` | `id` (UUID) | `conversation_id` -> `conversations.id` (`CASCADE`) | Short/medium-term chat turn history (`role`, `content`). |
| `memories` | `id` (UUID) | `user_id` -> `users.id` (`CASCADE`) | Selected long-term durable information (`type`, `key`, `value`, `importance`). |
| `ideas` | `id` (UUID) | `user_id` -> `users.id` (`CASCADE`) | Persistent store for startup ideas (`title`, `description`). |

### Why Conversation History and Durable Memory are Separate
* **`messages` (Conversation History)**: Captures recent, raw, sequential chat turns. They expire out of the prompt window as conversations progress to conserve context tokens.
* **`memories` (Durable Memory)**: Captures curated, permanent facts about the founder (e.g. project names, preferences, decisions). They survive indefinitely across different conversation sessions.

### Migration Strategy
Database tables are managed exclusively through **Alembic migrations** ([`alembic/versions/001_initial_schema.py`](file:///d:/REACT/founder-sidekick/backend/alembic/versions/001_initial_schema.py)) rather than `create_all()`, guaranteeing controlled, repeatable schema evolutions in production environments.

---

## 7. Agent & Persistent Tools

The agent layer uses **Agno** with **Google Gemini 2.5 Flash** (`gemini-2.5-flash`). Persistent tools are registered with clean docstrings and user-bound sessions:

1. `save_idea(title: str, description: str) -> dict`:
   Saves a new startup idea persistently to PostgreSQL for the current founder.
2. `get_idea(identifier: str) -> dict`:
   Retrieves a saved idea by title or UUID string.
3. `list_ideas() -> dict`:
   Lists all saved ideas owned by the founder.

Tools encapsulate all database logic inside `IdeaService`, keeping agent tool definitions free of raw SQL queries.

---

## 8. Context Management Strategy

To prevent blowing up prompt tokens and sending redundant history to the LLM, [`ContextManager`](file:///d:/REACT/founder-sidekick/backend/app/context/context_manager.py) constructs a bounded prompt context payload for each turn:

* **Bounded History**: Retrieves only the $N$ most recent messages (default `limit=10`) in chronological order.
* **Conversation Summary**: Includes `conversation.summary` if available to summarize earlier chat history.
* **Durable Memories**: Includes key long-term facts for `user_id` from the `memories` table.
* **Token Efficiency**: Keeps unneeded history out of the prompt window while preserving cross-session context.

---

## 9. API Reference

### 1. `GET /health`
Verifies backend service operational status and database connectivity.

**Response (200 OK)**:
```json
{
  "status": "healthy",
  "database": {
    "connected": true,
    "error": null
  }
}
```

---

### 2. `POST /chat`
Executes a chat turn with the Founder Sidekick AI Agent.

**Request Payload (`application/json`)**:
```json
{
  "user_id": "founder_123",
  "conversation_id": "conv_456",
  "message": "What did we call our developer tool?"
}
```

**Success Response (200 OK)**:
```json
{
  "user_id": "founder_123",
  "conversation_id": "conv_456",
  "response": "We called your developer tool RocketCat."
}
```

**Validation Error (422 Unprocessable Entity)**:
Returned when required fields (`user_id`, `conversation_id`, `message`) are missing or empty strings.

---

## 10. Local Setup & Execution Guide

### Prerequisites
* Python 3.11+
* PostgreSQL database instance (or Supabase PostgreSQL)

### Step 1: Clone Repository
```bash
git clone https://github.com/shivanifutureprofilez/founder-sidekick.git
cd founder-sidekick/backend
```

### Step 2: Create & Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env` and fill in your connection details:
```bash
cp .env.example .env
```

`.env` content:
```env
ENVIRONMENT=development
PORT=8000
HOST=0.0.0.0
DATABASE_URL=postgresql://user:password@host:5432/dbname
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### Step 5: Run Database Migrations
Apply the initial schema migration using Alembic:
```bash
alembic upgrade head
```

### Step 6: Start FastAPI Server
```bash
uvicorn app.main:app --reload --port 8000
```

### Step 7: Access Swagger / OpenAPI Documentation
Open your browser and navigate to:
* **Interactive Swagger UI**: `http://localhost:8000/docs`
* **ReDoc UI**: `http://localhost:8000/redoc`

---

## 11. Testing & Verification

The project includes an automated unit test suite built with Python's standard `unittest` framework.

### Run Automated Unit Tests
```bash
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

### Test Suite Execution Output
```
...............................
----------------------------------------------------------------------
Ran 31 tests in 0.788s

OK
```

### Test Coverage Summary (31 Tests Total)
* **Service Layer Tests (`test_services.py`)**: 15 tests covering CRUD, FK relationship integrity, cascade deletion, memory upserts, and idea operations.
* **Context Manager Tests (`test_context_manager.py`)**: 4 tests covering empty context handling, summary inclusion, durable memory user scoping, and message history truncation limit ($N=5$).
* **Idea Tool Tests (`test_idea_tools.py`)**: 6 tests covering save, get by title, get by ID, not-found error payloads, list ideas, and user data isolation.
* **Agent Integration Tests (`test_agent.py`)**: 2 tests covering Agno agent construction, tool registration, mocked turn execution, and database message turn persistence.
* **API Endpoint Tests (`test_api.py`)**: 4 tests covering `POST /chat` 200 OK responses, 422 validation errors, and PostgreSQL turn persistence.

---

## 12. Key Architectural Decisions

1. **PostgreSQL vs. Vector DB**:
   * For structured founder memories and persistent ideas, relational PostgreSQL queries provide exact match retrieval and multi-user isolation without embedding drift or vector index overhead.
2. **Alembic Migrations vs. `create_all()`**:
   * Using Alembic revision scripts ensures repeatable, version-controlled database migrations across development, staging, and production.
3. **Decoupled Service Layer**:
   * Services (`UserService`, `MemoryService`, `IdeaService`) encapsulate database operations, preventing direct SQL or ORM queries inside API routes or agent tools.
4. **Bounded Context Window**:
   * `ContextManager` enforces limits on recent history turns, preserving token budgets and keeping response latency low.
5. **Agno + Google Gemini 2.5 Flash**:
   * Agno provides lightweight agent orchestration and tool binding; Gemini 2.5 Flash provides high execution speed and tool-calling reliability.
