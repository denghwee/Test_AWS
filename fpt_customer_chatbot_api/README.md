# FPT Customer Support Chatbot API

A production-ready FastAPI application integrated with an advanced Multi-Agent AI Core (LangGraph) to handle customer support tickets, room bookings, and FAQ retrieval with Human-In-The-Loop (HITL) confirmation.

## 🚀 Setup Instructions

### 1. Prerequisites
*   Python 3.10+
*   SQLite (default) or any SQLAlchemy-compatible database.

### 2. Environment Configuration
Create a `.env` file in the `fpt_customer_chatbot_api/` directory:
```env
PROJECT_NAME="FPT Customer Chatbot API"
VERSION="1.0.0"
API_V1_STR="/api/v1"
SECRET_KEY="your-super-secret-key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database
SQLALCHEMY_DATABASE_URL="sqlite:///./fpt_chatbot.db"

# AWS RDS PostgreSQL. If this is set, it overrides SQLALCHEMY_DATABASE_URL.
DATABASE_URL="postgresql+psycopg2://postgres:<password>@<rds-endpoint>:5432/fastapi_prod"
DATABASE_SSLMODE="verify-full"
DATABASE_SSLROOTCERT="./global-bundle.pem"

# AI Core Configuration (Required)
OPENAI_API_KEY="sk-..."
TAVILY_API_KEY="tvly-..."

# AWS S3 file uploads
AWS_REGION="ap-southeast-1"
S3_BUCKET_NAME="fastapi-app-files-<your-id>"
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""
AWS_SESSION_TOKEN=""
```

### 3. Installation
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Linux/Mac: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Running the Application
```bash
# From the project root (FastAPI_Final)
uvicorn fpt_customer_chatbot_api.main:app --reload
```

---

## 📖 API Documentation

Once the server is running, access:
*   **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
*   **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Key Modules:
*   **Auth:** Login and JWT token generation.
*   **Users:** Role-based user management.
*   **Tickets:** Async CRUD for support tickets (Pending, InProgress, Resolved, Canceled).
*   **Bookings:** Intelligent room booking with datetime validation.
*   **Chat:** Multi-agent conversation with memory persistence and HITL.
*   **Files:** Authenticated file upload to a private Amazon S3 bucket.

---

## 🤖 AI Core & Architecture

### Multi-Agent Orchestration
The AI Core is built using **LangGraph**, enabling a stateful, branching conversation flow:
1.  **Primary Assistant:** Intelligent router using ReAct logic.
2.  **FAQ Agent:** High-performance retrieval using semantic caching.
3.  **IT Support Agent:** Specialized in technical troubleshooting and ticket automation.
4.  **Booking Agent:** Handles scheduling conflicts and room availability.

### Human-In-The-Loop (HITL) 2.0
*   **Sensitive Actions:** Operations like database mutations trigger an `interrupt`.
*   **Pending Confirmation:** The API returns a specialized response for the frontend to show confirmation UI.
*   **Tool Call Cancellation:** If a user sends a new message while an action is pending, the system automatically injects "cancellation" responses to the LLM to keep the state graph consistent and avoid errors.

### Semantic Caching Layer
*   **FAISS Integration:** Uses Vector similarity search for FAQ responses.
*   **TTL & CacheManager:** Implements Time-To-Live for cache entries to ensure data freshness while maintaining high performance.

---

## 🧪 Testing & Quality Assurance

### High Test Coverage: **92%**
The project implements a robust testing suite using `pytest` and `httpx`.

#### Coverage Report Summary:
| Module | Statements | Miss | Coverage |
| :--- | :---: | :---: | :---: |
| **Total Project** | **2161** | **179** | **92%** |
| `routers/auth.py` | 25 | 0 | 100% |
| `routers/bookings.py` | 52 | 2 | 96% |
| `routers/tickets.py` | 41 | 0 | 100% |
| `services/ai_adapter.py` | 78 | 10 | 87% |
| `services/agents/faq_agent.py` | 90 | 11 | 88% |
| `services/agents/it_support_agent.py` | 23 | 3 | 87% |
| `services/cache/faiss_cache.py` | 59 | 6 | 90% |
| `crud/bookings.py` | 37 | 3 | 92% |
| `models/ticket.py` | 25 | 2 | 92% |

**Consolidated Test Structure:**
*   `test_auth.py`: Covers authentication, users, security, and AI schemas.
*   `test_tickets.py`: Covers Ticket CRUD, Ticket tools, Chat router, and AI Adapter logic.
*   `test_bookings.py`: Covers Booking CRUD, Booking tools, FAISS Cache, and Graph routing.

**Run Tests:**
```bash
python -m pytest --cov=fpt_customer_chatbot_api fpt_customer_chatbot_api/tests -v
```

---

## 🛠 Tech Stack
*   **Backend:** FastAPI (Async/Await)
*   **Database:** SQLAlchemy 2.0 (Async), SQLite
*   **AI Framework:** LangChain, LangGraph
*   **Vector DB:** FAISS (Local)
*   **Embeddings:** Sentence-Transformers (all-MiniLM-L6-v2)
*   **Security:** JWT, Passlib (bcrypt)
*   **Monitoring:** Logging middleware with transaction tracing.
