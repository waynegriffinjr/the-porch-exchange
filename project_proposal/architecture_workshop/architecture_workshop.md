# The Blanchester Porch Exchange

A small-town community platform for skill trading, matching needs, and acting as a local resource gateway for Blanchester, Ohio.

Users can register, log in, create and manage needs / skill offers, and query local community resources through a RAG pipeline powered by ChromaDB + Ollama.

---

## API Endpoint Design

### FastAPI backend:
- `POST /auth/register` — create a new user account
- `POST /auth/login` — return a JWT access token
- `GET /users/me` — return the authenticated user’s profile
- `POST /needs/` — create a new community need / skill offer (auth required)
- `GET /needs/` — list the current user’s needs with optional filters (`completed`, `priority`) and pagination
- `GET /needs/{need_id}` — retrieve a single need (ownership checked)
- `PATCH /needs/{need_id}` — partially update a need
- `DELETE /needs/{need_id}` — delete a need
- `POST /needs/{need_id}/suggest` — return an AI-generated suggestion for the need (RAG / Ollama)
- Additional RAG endpoint(s) for querying loaded local documents

### SQLAlchemy database with at least 2 related tables
- **users** table: `id`, `username`, `email`, `hashed_password`
- **needs** table: `id`, `title`, `description`, `priority`, `completed`, `created_at`, `updated_at`, `owner_id`
- Relationship: one-to-many (one user owns many needs via foreign key `owner_id`)

### Pydantic validation on all endpoints
- Request models: `UserCreate`, `NeedCreate`, `NeedPatch`
- Response models: `UserResponse`, `TokenResponse`, `NeedResponse`
- Field constraints enforced (min/max length on title/description, `Literal` priority values, required fields, `from_attributes=True` for ORM responses)
- Used on every endpoint via `response_model=` and body parameters


### Docker Compose configuration (entire app runs with one command)
- Services: `backend` (FastAPI), `frontend` (Streamlit), `ollama`
- Single `docker-compose up` starts the full stack


services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    depends_on:
      - ollama

  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    depends_on:
      - backend

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  chroma_data:
  ollama_data:
  

























FieldTypeNotesidIntegerPrimary keyusernameStringUniqueemailStringUniquehashed_passwordStringNever returnedneeds

















































FieldTypeNotesidIntegerPrimary keytitleStringRequired, max 200descriptionStringOptional, max 2000priorityStringlow / medium / high / criticalcompletedBooleanDefault falsecreated_atDateTimeAuto-setupdated_atDateTimeAuto-updatedowner_idIntegerForeign key → users.idRelationship
One user → many needs (owner_id)
API Endpoint List
































































MethodPathAuth RequiredDescriptionPOST/auth/registerNoCreate a new user accountPOST/auth/loginNoReturn JWT access tokenGET/users/meYesReturn current user profilePOST/needs/YesCreate a new need / skill offerGET/needs/YesList current user’s needs (filters + pagination)GET/needs/{need_id}YesGet a single need (ownership checked)PATCH/needs/{need_id}YesPartially update a needDELETE/needs/{need_id}YesDelete a needPOST/needs/{need_id}/suggestYesAI suggestion for the need (RAG / Ollama)All authenticated routes require a valid Authorization: Bearer <token> header.

Cross-user access returns 403.Docker Compose Service PlanYAMLservices:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data
    depends_on:
      - ollama

  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    depends_on:
      - backend

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:Start commandBashdocker-compose up --buildUsage Guide
Register an account
Open the Streamlit app → create a username, email, and password.
Log in
Enter credentials → JWT is issued and stored in the session → redirected to dashboard.
Manage needs / skill offers
Create, view, filter, update, or delete your needs. Use the Suggest action for an AI recommendation.
Query local resources (RAG tab)
Switch to the Resource RAG tab and ask questions about Blanchester community resources, skills, or town services.
View metrics
Open the Metrics tab for need counts, priority breakdowns, and completion stats.
Two Risks & Backup PlansRisk 1: Ollama / RAG pipeline fails or is too slowWhat might go wrong

Ollama is not running, the model is not pulled, ChromaDB has no documents, or latency is too high.Backup plan
Health-check endpoint verifies Ollama and ChromaDB.
Fallback message if RAG fails.
Cache recent successful responses.
Document manual start steps and include checks in Docker Compose.
Risk 2: Authentication or data-ownership bugs leak user dataWhat might go wrong

Missing auth dependency or incorrect owner check allows one user to access another user’s needs.Backup plan
Every need route uses get_current_user and filters by owner_id.
Automated tests cover 401, 403, and ownership isolation.
Short JWT expiry (30 minutes).
Never return hashed_password.
Test Requirements
Listed in requirements-dev.txt: pytest, httpx, pytest-cov
Tests live in tests/ and use a separate SQLite test database (test.db) that is reset per test.
Run with:Bashpip install -r requirements-dev.txt
pytest