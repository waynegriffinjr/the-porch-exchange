# Project name and one-sentence description
I would like to create 'The Blanchester Porch Exchange.' It is a small community resource skill trading, needs meeting, and resource gateway.


# User story: "As a [user], I want to [action] so that [benefit]"

As a neighbor, I want to share my skills so that I can meet others needs and have others meet my needs.


# Required components checklist: How each required component maps to your project

## FastAPI backend with at least 3 endpoints
- `POST /auth/register` — create a new user account
- `POST /auth/login` — return a JWT access token
- `GET /users/me` — return the authenticated user’s profile
- `POST /needs/` — create a new community need / skill offer (auth required)
- `GET /needs/` — list the current user’s needs with optional filters (`completed`, `priority`) and pagination
- `GET /need/{need_id}` — retrieve a single need (ownership checked)
- `PATCH /needs/{need_id}` — partially update a need
- `DELETE /needs/{need_id}` — delete a need
- `POST /needs/{need_id}/suggest` — return an AI-generated suggestion for community support resources (RAG / Ollama)
- Additional RAG endpoint(s) for querying loaded local documents

## SQLAlchemy database with at least 2 related tables
- **users** table: `id`, `username`, `email`, `hashed_password`
- **needs** table: `id`, `title`, `description`, `priority`, `completed`, `created_at`, `updated_at`, `owner_id`
- Relationship: one-to-many (one user owns many needs via foreign key `owner_id`)

## Pydantic validation on all endpoints
- Request models: `UserCreate`, `NeedCreate`, `NeedPatch`
- Response models: `UserResponse`, `TokenResponse`, `TaskResponse`
- Field constraints enforced (min/max length on title/description, `Literal` priority values, required fields, `from_attributes=True` for ORM responses)
- Used on every endpoint via `response_model=` and body parameters

## JWT authentication
- Passwords hashed with bcrypt (`passlib`)
- JWT created with `python-jose`, HS256, 30-minute expiry, `SECRET_KEY` from environment
- `OAuth2PasswordBearer(tokenUrl="/auth/login")`
- `get_current_user` dependency decodes the token, looks up the user, and protects all task routes
- Unauthenticated requests return 401; cross-user access returns 403

## RAG pipeline (ChromaDB + Ollama or API-based LLM)
- Local documents (Blanchester community resources, skill guides, town services, how-tos) loaded into **ChromaDB**
- **Ollama** used as the LLM for generation
- Retrieval + generation used by the need suggestion endpoint and by a dedicated resource Q&A tab in the frontend

## Streamlit frontend
- Login page (username/password → JWT stored in session)
- User dashboard showing the authenticated user’s needs / skillset
- Tab for metrics (need counts, priority breakdown, completed vs open, etc.)
- Tab for resource RAG (chat-style interface that queries ChromaDB + Ollama about local community resources)

## Docker Compose configuration (entire app runs with one command)
- Services: `backend` (FastAPI), `frontend` (Streamlit), `ollama`
- Single `docker-compose up` starts the full stack (database can be SQLite volume or an additional Postgres service if added)

## At least 5 passing tests
- Unauthenticated request to `/needs/` returns 401
- Authenticated user can create a need (201 + correct body)
- User can list only their own needs
- User can retrieve need by ID
- Missing need returns 404
- Needs can be filtered by `completed`/`priority` and paginated
- Partial update preserves omitted fields
- Profile endpoint returns user data without password; suggestion endpoint returns a suggestion

## Usage Guide
### Register an account
Open the Streamlit app
Go to the login/register page
Create a username, email, and password

### Log in
Enter your credentials
A JWT is issued and stored in the session
You are redirected to your dashboard

### Manage needs / skill offers
Create a new need with title, description, and priority (low / medium / high / critical)
View, filter, and paginate your needs
Update or delete needs you own
Use the Suggest action to get an AI-generated recommendation

### Query local resources (RAG tab)
Switch to the Resource RAG tab
Ask questions about Blanchester community resources, skills, town services, or how-tos
The backend retrieves relevant documents from ChromaDB and generates an answer with Ollama

### View metrics
Open the Metrics tab to see counts of open vs completed tasks, priority breakdowns, etc.

## requirements.txt (or per-service requirements files)
- Backend `requirements.txt`:
fastapi==0.109.0
uvicorn==0.27.0
chromadb==0.4.22
requests==2.31.0
pydantic
python-jose
passlib[bcrypt]
python-dotenv
httpx
ollama

- Frontend `requirements.txt`:
streamlit==1.39.0
requests==2.31.0

## Test requirements
- Listed in `requirements-dev.txt` (or under a `[dev]` extra in `requirements.txt`)
- Core packages: `pytest`, `httpx`, `pytest-cov`
- Optional but useful: `pytest-asyncio` (if any async tests are added later)
- Tests live in `tests/` and can be run with:
  ```bash
  pip install -r requirements-dev.txt
  pytest
All tests use a separate SQLite test database (test.db) that is created and destroyed per test via fixtures, so the main application database is never touched.


# Data source: What documents will your RAG pipeline use?
Documents come from Blanchester community resource pages and Clinton County resource pages.

# Tech stack confirmation: 

FastAPI + SQLAlchemy + ChromaDB + Ollama + Streamlit + Docker

# Two risks: What might go wrong? What’s your backup plan?

## Risk 1: Ollama / RAG pipeline fails or is too slow
**What might go wrong**  
Ollama is not running, the model is not pulled, ChromaDB has no documents loaded, or response latency is too high for a good user experience.

**Backup plan**  
- Add a health-check endpoint that verifies Ollama and ChromaDB are reachable.  
- If the RAG call fails, return a clear fallback message (e.g. “Resource search is temporarily unavailable — try again later or browse tasks manually”).  
- Cache recent successful RAG responses for common queries.  
- Document a simple manual start command (`ollama serve` + `ollama pull <model>`) and include a check in the Docker Compose startup.

## Risk 2: Authentication or data-ownership bugs leak user data
**What might go wrong**  
A missing `Depends(get_current_user)` or incorrect owner check lets one user view, edit, or delete another user’s tasks.

**Backup plan**  
- Every need route requires the `get_current_user` dependency and explicitly filters by `owner_id == current_user.id`.  
- Automated tests cover: unauthenticated requests return 401, cross-user access returns 403, and users only see their own tasks.  
- Run the test suite in CI before merging.  
- Keep JWT expiry short (30 minutes) and never return `hashed_password` in any response model.