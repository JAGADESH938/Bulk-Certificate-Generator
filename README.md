# Bulk Certificate Generator Backend

A high-performance, production-ready Python backend API designed to handle bulk certificate generation at scale. The service validates recipient data, creates an asynchronous background generation job, renders high-resolution PDF certificates using ReportLab, isolates individual failures so batches never fail catastrophically, and serves generated PDF certificates via streaming download endpoints.

---

## 🌟 Key Features

- **Asynchronous Non-Blocking Execution**: Jobs return `HTTP 202 Accepted` immediately, offloading computationally intensive PDF rendering to isolated background workers.
- **Transactional Failure Isolation**: Each recipient's certificate generation runs in its own sub-transaction. A failed certificate (e.g. malformed data or rendering error) will **not** roll back or abort other successful certificates.
- **Accurate Job State Tracking**: Real-time tracking of `total_count`, `successful_count`, `failed_count`, `pending_count`, and calculated `progress_percentage`.
- **Vector PDF Rendering**: High-resolution, professional certificates rendered on-the-fly with ReportLab, featuring multi-tier ornamental borders, verification seals, and unique certificate identifiers.
- **Secure File Storage**: Follows 12-factor application architecture by keeping large binary files on durable filesystem storage (`storage/certificates/{job_id}/{certificate_id}.pdf`) rather than bloating PostgreSQL relational tables.
- **Modular Architecture**: Layered separation of concerns with dependency injection for database sessions and swappable worker abstractions (easily interchangeable with Celery or RQ without altering API routes).
- **Strict Data Validation**: Pydantic v2 validation enforcing email correctness, string sanitization, deduplication of recipient emails per batch, and maximum bulk limits.

---

## 🏗️ Architecture Overview

The application follows a clean, layered architectural design:

```
app/
├── main.py                  # FastAPI application entrypoint, middleware & exception handlers
├── core/
│   ├── config.py            # Pydantic Settings configuration from environment variables
│   └── database.py          # SQLAlchemy 2.x engine, sessionmaker & Base declarative model
├── models/
│   ├── generation_job.py    # GenerationJob model & JobStatus enum
│   └── certificate.py       # Certificate model & CertificateStatus enum
├── schemas/
│   ├── generation.py        # Pydantic schemas for job creation & status responses
│   └── certificate.py       # Pydantic schemas for recipients, certificates & pagination
├── api/
│   └── routes/
│       ├── jobs.py          # API route controllers for /api/v1/jobs
│       └── certificates.py  # API route controllers for /api/v1/certificates
├── services/
│   ├── generation_service.py # Job creation, database queries & pagination logic
│   ├── certificate_service.py# ReportLab PDF template rendering engine
│   └── storage_service.py   # Pathlib-based filesystem storage operations
├── workers/
│   └── certificate_worker.py# Decoupled background task worker & queue abstraction
├── templates/
│   └── certificate_template.pdf # Reference PDF certificate layout
└── utils/
    └── validation.py        # Normalization and string sanitization utilities
```

### Component Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client
    participant API as FastAPI Route (POST /jobs)
    participant DB as PostgreSQL
    participant Worker as Background Worker
    participant Storage as File Storage (Disk)

    Client->>API: POST /api/v1/jobs (JSON payload)
    API->>API: Validate schema & check duplicate emails
    API->>DB: INSERT GenerationJob (PENDING) & Certificates (PENDING)
    DB-->>API: Commit transaction
    API->>Worker: Dispatch job ID to background task
    API-->>Client: HTTP 202 Accepted {job_id, status: "PENDING"}

    par Background Processing
        Worker->>DB: UPDATE GenerationJob status = "PROCESSING"
        loop For each Certificate
            Worker->>DB: UPDATE Certificate status = "PROCESSING"
            Worker->>Worker: Render PDF via ReportLab
            alt Generation Successful
                Worker->>Storage: Save PDF to storage/certificates/{job_id}/{cert_id}.pdf
                Worker->>DB: UPDATE Certificate status="COMPLETED", file_path=..., job.successful_count += 1
            else Generation Failed
                Worker->>DB: UPDATE Certificate status="FAILED", error_message=..., job.failed_count += 1
            end
        end
        Worker->>DB: UPDATE GenerationJob status = COMPLETED / COMPLETED_WITH_ERRORS / FAILED
    end

    Client->>API: GET /api/v1/jobs/{job_id}
    API->>DB: Query job & calculate progress %
    DB-->>API: Job counts
    API-->>Client: HTTP 200 OK (Job status & progress)

    Client->>API: GET /api/v1/certificates/{id}/download
    API->>Storage: Fetch PDF file
    Storage-->>API: File stream
    API-->>Client: HTTP 200 FileResponse (application/pdf)
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Language** | Python 3.12+ (tested on Python 3.12 & 3.13) |
| **Framework** | FastAPI (ASGI web framework) |
| **Server** | Uvicorn with standard ASGI workers |
| **Database** | PostgreSQL 16 (psycopg 3 driver) / SQLite for fast local tests |
| **ORM** | SQLAlchemy 2.x (Mapped columns & type annotations) |
| **Migrations** | Alembic |
| **Data Validation** | Pydantic v2 & `pydantic-settings` |
| **PDF Generation** | ReportLab 4.x / 5.x |
| **Testing** | Pytest, Pytest-Asyncio, HTTPX / Starlette TestClient |
| **Containerization** | Docker & Docker Compose |

---

## 📋 Prerequisites

- **Python**: Version 3.12 or higher
- **Docker & Docker Compose**: Optional, for containerized execution
- **Git**

---

## ⚙️ Environment Configuration

Configuration is managed through environment variables loaded via Pydantic Settings.

Copy `.env.example` to create your local `.env`:

```bash
cp .env.example .env
```

### Configurable Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql+psycopg://postgres:postgres@db:5432/certificate_db` |
| `STORAGE_PATH` | Filesystem path for generated PDFs | `storage/certificates` |
| `MAX_RECIPIENTS_PER_JOB` | Maximum allowed recipients in a single request | `1000` |
| `ENVIRONMENT` | Runtime environment (`development`, `production`, `testing`) | `development` |
| `PROJECT_NAME` | OpenAPI and application title | `Bulk Certificate Generator` |
| `API_V1_PREFIX` | Versioned route prefix | `/api/v1` |

---

## 🚀 Quickstart & Setup

### 1. Running with Docker Compose (Recommended)

Docker Compose starts PostgreSQL and the FastAPI application in isolated containers with automated volume mounting and health checks.

```bash
# Build images and start all services
docker compose up --build -d

# View application logs
docker compose logs -f api

# Stop all services
docker compose down
```

The API is now accessible at `http://localhost:8000`.
Interactive Swagger UI is available at `http://localhost:8000/docs`.

---

### 2. Local Setup (Without Docker)

#### Step 1: Create and Activate Virtual Environment

**On Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### Step 2: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 3: Run Database Migrations
Make sure your PostgreSQL server is running (or point `DATABASE_URL` to SQLite for local development: `DATABASE_URL=sqlite:///./dev.db`).

```bash
alembic upgrade head
```

#### Step 4: Start the Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Running Automated Tests

The test suite covers validation, job lifecycle, concurrent failure isolation, metadata retrieval, pagination, and ReportLab PDF file generation.

```bash
# Run all tests with pytest
pytest -v

# Run with coverage report
pytest --cov=app tests/
```

All tests execute in an isolated in-memory database with temporary file storage fixtures that clean up automatically.

---

## 📖 API Endpoints Reference

### 1. Create Generation Job
- **Method**: `POST /api/v1/jobs`
- **Status**: `202 Accepted`
- **Description**: Validates recipient data and dispatches background generation task.

#### Request Example:
```json
{
  "certificate_title": "Python Specialist Certification",
  "certificate_date": "2026-10-07",
  "recipients": [
    {
      "name": "Alice Johnson",
      "email": "alice@example.com"
    },
    {
      "name": "Bob Smith",
      "email": "bob@example.com"
    }
  ]
}
```

#### Response Example:
```json
{
  "job_id": "c1f7b539-77ba-4ee0-bbd8-4f810aa7fae2",
  "status": "PENDING",
  "total_count": 2,
  "message": "Certificate generation job accepted"
}
```

---

### 2. Get Job Status and Progress
- **Method**: `GET /api/v1/jobs/{job_id}`
- **Status**: `200 OK`
- **Description**: Retrieves real-time job status, completion counters, and percentage progress.

#### Response Example:
```json
{
  "job_id": "c1f7b539-77ba-4ee0-bbd8-4f810aa7fae2",
  "status": "COMPLETED",
  "total_count": 100,
  "successful_count": 98,
  "failed_count": 2,
  "pending_count": 0,
  "progress_percentage": 100.0,
  "created_at": "2026-10-07T01:30:00Z",
  "started_at": "2026-10-07T01:30:01Z",
  "completed_at": "2026-10-07T01:30:15Z",
  "error_message": null,
  "certificates": null
}
```

---

### 3. List Certificates for a Job (Paginated)
- **Method**: `GET /api/v1/jobs/{job_id}/certificates`
- **Parameters**:
  - `page`: Page number (default: `1`, minimum: `1`)
  - `page_size`: Records per page (default: `20`, maximum: `100`)
  - `status`: Optional status filter (`PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`)
- **Status**: `200 OK`

#### Response Example:
```json
{
  "items": [
    {
      "id": "7b8f9e21-0a44-42b7-a02d-083b8b1dc9b2",
      "job_id": "c1f7b539-77ba-4ee0-bbd8-4f810aa7fae2",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "certificate_title": "Python Specialist Certification",
      "certificate_date": "2026-10-07",
      "certificate_id": "CERT-F8E39A2B4C1D",
      "status": "COMPLETED",
      "file_path": "storage/certificates/c1f7b539.../7b8f9e21....pdf",
      "error_message": null,
      "created_at": "2026-10-07T01:30:00Z",
      "completed_at": "2026-10-07T01:30:02Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

### 4. Get Certificate Metadata
- **Method**: `GET /api/v1/certificates/{certificate_id}`
- **Parameters**: `certificate_id` (Accepts either database UUID or credential identifier like `CERT-F8E39A2B4C1D`)
- **Status**: `200 OK`

---

### 5. Download Certificate PDF
- **Method**: `GET /api/v1/certificates/{certificate_id}/download`
- **Status**: `200 OK` (`application/pdf`)
- **Error Codes**:
  - `400 Bad Request`: Certificate generation failed (details in response).
  - `404 Not Found`: Certificate or file does not exist.
  - `409 Conflict`: Certificate is still being generated (`PENDING` or `PROCESSING`).

---

## 💻 Sample cURL Commands

### 1. Create a Bulk Job
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "certificate_title": "Full-Stack Python Engineer",
    "certificate_date": "2026-10-07",
    "recipients": [
      {"name": "Ada Lovelace", "email": "ada@lovelace.io"},
      {"name": "Alan Turing", "email": "alan@turing.org"}
    ]
  }'
```

### 2. Check Job Status
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/<JOB_UUID>"
```

### 3. List Job Certificates
```bash
curl -X GET "http://localhost:8000/api/v1/jobs/<JOB_UUID>/certificates?page=1&page_size=10"
```

### 4. Download Certificate PDF
```bash
curl -X GET "http://localhost:8000/api/v1/certificates/<CERTIFICATE_UUID>/download" \
  --output certificate.pdf
```


rver.
> 4. Add a read replica for PostgreSQL to handle high-frequency status polling queries without impacting write performance.
