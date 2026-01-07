# SmartChatAI Backend

FastAPI backend for SmartChatAI - an AI-powered chat application with document analysis and resume tools.

## Features

- 🔐 **Authentication**: Firebase Auth with email/password and Google OAuth
- 💬 **AI Chat**: Conversational AI using Google Gemini with context-aware responses
- 📄 **Document Q&A**: Upload documents and ask questions using RAG (Retrieval Augmented Generation)
- 📝 **Resume Analysis**: Analyze resumes against job descriptions with detailed scoring and recommendations
- 📊 **Usage Limits**: Free tier quotas with admin management
- 🎫 **Help & Support**: Ticket system for user support
- 📄 **PDF Generation**: Generate professional resume PDFs from templates
- 🏗️ **Production-Ready**: Clean architecture with dependency injection, decorators, and service layer

## Tech Stack

- **Framework**: FastAPI
- **Database**: Google Cloud Firestore
- **Authentication**: Firebase Admin SDK
- **AI**: Google Gemini 2.5 Flash
- **Vector DB**: FAISS (for document search)
- **Embeddings**: Gemini Embeddings API (batch processing)
- **PDF Generation**: Playwright + Jinja2
- **Package Manager**: Poetry

## Application Flow Diagrams

### 🔐 Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant Firebase Auth
    participant Firestore

    User->>Frontend: Login/Signup
    Frontend->>Firebase Auth: Authenticate
    Firebase Auth-->>Frontend: idToken + refreshToken
    Frontend->>Frontend: Store tokens (localStorage)
    Frontend->>Backend: API Request + Bearer Token
    Backend->>Backend: Verify Token (Firebase Admin)
    Backend->>Firestore: Get/Update User Data
    Firestore-->>Backend: User Document
    Backend-->>Frontend: Response
```

### 💬 Chat Flow

```mermaid
flowchart TD
    A[User Sends Message] --> B{Session Exists?}
    B -->|No| C[Check Session Limit<br/>Max 2 sessions]
    B -->|Yes| D[Check Message Limit<br/>Max 30 per session]
    C --> E[Create New Session]
    D --> F[Update Session Timestamp]
    E --> G[Save User Message to Firestore]
    F --> G
    G --> H[Get Last 10 Messages]
    H --> I[Call Gemini API]
    I --> J[Save AI Response to Firestore]
    J --> K[Return Reply to Frontend]
    
    style C fill:#ffcccc
    style D fill:#ffcccc
    style I fill:#ccffcc
```

### 📄 Document Upload & Processing Flow

```mermaid
flowchart TD
    A[User Uploads Document] --> B[Check Document Limit<br/>Max 2 documents]
    B --> C{Within Limit?}
    C -->|No| D[Return 403 Error]
    C -->|Yes| E[Save File Temporarily]
    E --> F[Extract Text from PDF/DOCX]
    F --> G[Token-Based Chunking<br/>~1500 tokens per chunk]
    G --> H[Batch Embedding API Call<br/>Up to 100 chunks at once]
    H --> I[Create FAISS Vectorstore]
    I --> J[Save Metadata to Firestore]
    J --> K[Return Processing Status]
    
    style B fill:#ffcccc
    style H fill:#ccffcc
    style I fill:#ccffcc
```

### 📝 Resume Analysis Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant Backend
    participant UsageService
    participant ResumeService
    participant Gemini API
    participant Firestore

    User->>Frontend: Upload Resume + JD
    Frontend->>Backend: POST /resume/compare-resume-jd
    Backend->>UsageService: Check Resume Limit
    UsageService->>Firestore: Get resume_generation_count
    Firestore-->>UsageService: Count
    UsageService-->>Backend: Allow/Deny
    Backend->>ResumeService: Extract Resume Text
    ResumeService->>ResumeService: Parse PDF
    ResumeService->>Gemini API: Analyze Resume vs JD
    Gemini API-->>ResumeService: Analysis JSON
    ResumeService->>Firestore: Increment Counter
    ResumeService-->>Backend: Analysis Result
    Backend-->>Frontend: Scores + Recommendations
```

### 📊 Usage Limits & Admin Flow

```mermaid
flowchart TD
    A[User Action Request] --> B{User Role?}
    B -->|Admin| C[Unlimited Access]
    B -->|Regular User| D[Check Usage Limits]
    D --> E{Sessions<br/>Max 2}
    D --> F{Documents<br/>Max 2}
    D --> G{Resumes<br/>Max 2}
    D --> H{Messages<br/>Max 30/session}
    E --> I{Within Limit?}
    F --> I
    G --> I
    H --> I
    I -->|Yes| J[Process Request]
    I -->|No| K[Return 403 Error]
    C --> J
    
    L[Admin Dashboard] --> M[View All Users Usage]
    M --> N[Reset User Limits]
    N --> O[Update Firestore]
    
    style C fill:#ccffcc
    style K fill:#ffcccc
```

### 🎫 Help & Support Flow

```mermaid
flowchart LR
    A[User Submits Query] --> B[Save to Firestore<br/>status: open]
    B --> C[Admin Views Queries]
    C --> D{Filter by Status?}
    D -->|Yes| E[Filter: open/in_progress/resolved/closed]
    D -->|No| F[Show All Queries]
    E --> G[Admin Replies]
    F --> G
    G --> H[Update Query<br/>status: in_progress]
    H --> I[User Views Response]
    I --> J[Admin Updates Status<br/>resolved/closed]
    
    style A fill:#ccffcc
    style G fill:#ffffcc
    style J fill:#ccccff
```

### 📄 PDF Generation Flow

```mermaid
flowchart TD
    A[User Requests PDF] --> B[Select Template<br/>modern/minimal/tech]
    B --> C[Load Jinja2 Template]
    C --> D[Inject Resume Data]
    D --> E[Render HTML]
    E --> F[Launch Playwright Browser]
    F --> G[Set HTML Content]
    G --> H[Generate PDF<br/>A4 Format]
    H --> I[Return PDF Bytes]
    I --> J[Download Response]
    
    style C fill:#ccffcc
    style F fill:#ffcccc
    style H fill:#ccccff
```

### 🔄 Complete Request Flow (Example: Chat)

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Dependency
    participant Security
    participant Service
    participant Firestore
    participant Gemini API

    Client->>FastAPI: POST /chat/send-message<br/>+ Bearer Token
    FastAPI->>Dependency: get_current_user()
    Dependency->>Security: verify_firebase_token()
    Security->>Security: Extract & Verify Token
    Security-->>Dependency: Decoded Token (uid, email)
    Dependency-->>FastAPI: current_user dict
    FastAPI->>Service: send_message()
    Service->>Service: Check Usage Limits
    Service->>Firestore: Save Message
    Service->>Firestore: Get History
    Service->>Gemini API: Generate Response
    Gemini API-->>Service: AI Reply
    Service->>Firestore: Save Reply
    Service-->>FastAPI: Response Data
    FastAPI-->>Client: JSON Response
```

## Project Structure

```
smartchatAI-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app initialization
│   ├── config.py               # Settings management
│   ├── dependencies.py         # Dependency injection
│   ├── decorators.py           # Route decorators
│   ├── api/
│   │   ├── v1/
│   │   │   ├── auth.py         # Authentication routes
│   │   │   ├── chat.py         # Chat routes
│   │   │   ├── document.py     # Document Q&A routes
│   │   │   ├── resume.py       # Resume analysis routes
│   │   │   ├── usage.py        # Usage & admin routes
│   │   │   └── help.py         # Help & support routes
│   ├── core/
│   │   ├── security.py         # Auth utilities
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── gemini_embeddings.py # Batch embedding service
│   ├── services/
│   │   ├── auth_service.py     # Auth business logic
│   │   ├── chat_service.py     # Chat business logic
│   │   ├── document_service.py # Document processing logic
│   │   ├── resume_service.py   # Resume analysis logic
│   │   ├── usage_limit_service.py # Usage quota management
│   │   ├── help_service.py     # Help ticket management
│   │   └── pdf_service.py      # PDF generation service
│   ├── models/
│   │   └── schemas.py          # Pydantic models
│   ├── db/
│   │   └── firestore_client.py # Firestore client
│   └── templates/
│       └── resume/             # PDF templates
│           ├── modern.html
│           ├── minimal.html
│           └── tech.html
├── pyproject.toml              # Poetry configuration
├── .env.example               # Environment variables template
└── README.md
```

## Setup

### Prerequisites

- Python 3.11+
- Poetry
- Firebase project with Firestore enabled
- Google Gemini API key
- Playwright (for PDF generation)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd smartchatAI-backend
```

2. **Install Poetry** (if not already installed)
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

3. **Install dependencies**
```bash
poetry install
```

4. **Install Playwright browser** (for PDF generation)
```bash
playwright install chromium
```

5. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

6. **Activate Poetry shell**
```bash
poetry shell
```

7. **Run the application**
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication (`/auth`)
- `POST /auth/login` - Login with email/password
- `POST /auth/signup` - Create new account
- `POST /auth/google-signup` - Sign up with Google
- `GET /auth/me` - Get current user
- `POST /auth/update-me` - Update profile
- `POST /auth/update-password` - Change password

### Chat (`/chat`)
- `POST /chat/send-message` - Send message and get AI response
- `GET /chat/sessions` - Get all user sessions
- `GET /chat/sessions/{id}` - Get session details
- `GET /chat/sessions/{id}/messages` - Get session messages
- `DELETE /chat/sessions/{id}` - Delete session

### Document Chat (`/document`)
- `POST /document/upload` - Upload document for processing
- `GET /document/status` - Check processing status
- `POST /document/ask` - Ask question about document
- `DELETE /document/{id}` - Delete document

### Resume (`/resume`)
- `POST /resume/compare-resume-jd` - Analyze resume against job description
- `POST /resume/generate-resume` - Generate/formatted resume JSON
- `POST /resume/generate-pdf` - Generate PDF from resume data

### Usage & Admin (`/usage`)
- `GET /usage/my-usage` - Get current user's usage stats
- `GET /usage/all-users` - Get all users' usage (Admin only)
- `GET /usage/user-usage/{id}` - Get specific user's usage (Admin only)
- `POST /usage/reset/{id}` - Reset user's usage limits (Admin only)

### Help & Support (`/help`)
- `POST /help/queries` - Submit support query
- `GET /help/queries` - Get user's own queries
- `GET /help/queries/all` - Get all queries (Admin only)
- `POST /help/queries/{id}/reply` - Reply to query (Admin only)
- `PATCH /help/queries/{id}/status` - Update query status (Admin only)

## Usage Limits (Free Tier)

- **Chat Sessions**: 2 per user
- **Messages per Session**: 30
- **Documents**: 2 per user
- **Resume Generations**: 2 per user
- **Admin Users**: Unlimited access

## Development

### Code Formatting
```bash
poetry run black app/
poetry run ruff check app/
```

### Type Checking
```bash
poetry run mypy app/
```

## Performance Optimizations

1. **Batch Embeddings**: Documents are embedded in batches of 100 (70x faster for large files)
2. **Token-Based Chunking**: More accurate than character-based chunking
3. **Stateless Authentication**: No server-side session storage
4. **Efficient Queries**: Python-side sorting to avoid Firestore composite index requirements

## Architecture Highlights

- **Dependency Injection**: FastAPI's dependency system for auth and database access
- **Decorators**: Custom decorators for error handling and authentication
- **Service Layer**: Business logic separated from route handlers
- **Pydantic Models**: Request/response validation with schemas
- **Configuration Management**: Centralized settings with pydantic-settings
- **Admin System**: Role-based access control with Firestore

## License

[Your License Here]
