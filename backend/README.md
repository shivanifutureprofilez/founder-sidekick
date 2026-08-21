# Founder Sidekick — API-First AI Agent

**Founder Sidekick** is an API-first AI companion for startup founders. It maintains context-aware chat turns, retains long-term durable founder facts across sessions, manages prompt token context, and executes persistent database operations using structured agent tools.

---

## 1. Quick Setup & Verification

```bash
# 1. Environment & Dependencies
python -m venv .venv
.\.venv\Scripts\activate       # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

# 2. Database Migrations & Run Server
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Interactive API Docs
# Open http://localhost:8000/docs in your browser

# 4. Run Full Unit Test Suite (31 Tests)
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

---

## 2. Tech Stack & Request Flow

* **Stack**: Python 3.11+, FastAPI, Agno (`2.9.0`), Google Gemini 2.5 Flash (`google-genai`), SQLAlchemy 2.x, PostgreSQL (Supabase), Alembic.

### Execution Flow (`POST /chat`)
1. **Endpoint**: `POST /chat` receives `{ user_id, conversation_id, message }`.
2. **Entity Assurance**: `UserService` and `ConversationService` guarantee User and Conversation records exist in PostgreSQL.
3. **Context Assembly**: `ContextManager` fetches conversation summary, durable memories, and recent $N$ messages.
4. **Message Persistence**: `MessageService` saves incoming user message and outgoing assistant reply to PostgreSQL.
5. **Agent Execution**: Agno Agent passes prompt to Gemini 2.5 Flash, executing persistent tools (`save_idea`, `get_idea`, `list_ideas`) via `IdeaService` if requested.

---

## 3. Memory Model vs. Conversation History

The architecture strictly separates short-term turn history from durable long-term memory:

| Entity | Table | Lifespan & Purpose | Behavior |
| :--- | :--- | :--- | :--- |
| **Conversation History** | `messages` | Short/medium-term session turns (`role`, `content`). | Truncated to the recent $N$ messages ($N=10$) to keep prompt tokens bounded. |
| **Durable Memory** | `memories` | Permanent founder facts (`type`, `key`, `value`, `importance`). | Persists indefinitely across different conversation sessions (e.g. project names, preferences, strategic decisions). |

---

## 4. Context Strategy

To avoid blindly sending unlimited chat history or wasting LLM token budget:
* **Bounded History Window**: Only the $N$ most recent messages (default `limit=10`) are fetched in chronological order.
* **Summary Integration**: If `conversation.summary` exists, it is injected into system context to preserve historical context beyond the recent $N$ turns.
* **Durable Facts Injection**: Active `memories` for `user_id` are injected into system prompt so the agent remembers founder context across sessions.

---

## 5. Agent Tools & Choices

The agent layer binds 3 PostgreSQL-backed tools encapsulated inside `IdeaService`:
* `save_idea(title, description)`: Persistently stores a startup idea in PostgreSQL.
* `get_idea(identifier)`: Retrieves a saved idea by title or UUID string.
* `list_ideas()`: Lists all saved startup ideas scoped to the founder.

**Tool Choice Rationale**: Wrapping database logic inside `IdeaService` ensures agent tool definitions stay clean, exposing only domain parameters (`title`, `description`, `identifier`) without embedding raw SQL or ORM queries inside the agent layer.

---

## 6. Design Trade-offs

1. **Relational PostgreSQL vs. Vector Database**:
   * *Trade-off*: Used PostgreSQL exact queries instead of a Vector DB (pgvector / RAG).
   * *Reasoning*: Structured founder facts and persistent ideas require exact matching, strict user isolation, and fast CRUD operations without embedding model latency or index drift.
2. **Alembic Migrations vs. `create_all()`**:
   * *Trade-off*: Explicit revision scripts (`001_initial_schema.py`) over auto-creating tables on app startup.
   * *Reasoning*: Guarantees version-controlled, production-safe database schema evolution.
3. **Decoupled Application Service Layer**:
   * *Trade-off*: Separate service classes (`UserService`, `MemoryService`, `IdeaService`) over inline route/agent logic.
   * *Reasoning*: Simplifies unit testing (31 passing tests) and prevents SQL leaking into routes or tools.

---

## 7. What Would You Change at Larger Scale?

If scaling this system to handle millions of founders and high-concurrency traffic:

1. **Async Database Driver & Connection Pooling**:
   * Migrate SQLAlchemy from `psycopg2-binary` (sync) to `asyncpg` (async) with PgBouncer connection pooling to avoid blocking worker threads during high LLM call concurrency.
2. **Hybrid & Vector Memory Retrieval**:
   * As durable memory records grow into thousands per user, add `pgvector` for semantic search (hybrid BM25 + vector similarity) so only the top-$K$ most relevant memories are injected into the prompt.
3. **Async Background Memory Extraction**:
   * Offload durable memory extraction and conversation summarization to asynchronous Celery/Redis background workers, keeping API request latency minimal.
4. **Redis Cache Layer**:
   * Cache recent context windows and active founder memories in Redis with pub/sub invalidation for sub-millisecond context assembly.
5. **Streaming API Responses (SSE / WebSockets)**:
   * Expose `POST /chat/stream` with Server-Sent Events (SSE) so founders receive real-time streaming tokens from Gemini.
