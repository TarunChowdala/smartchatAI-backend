# SmartChatAI Backend

FastAPI backend for SmartChatAI - an AI-powered chat application with document analysis and resume tools.

## Features

- 🔐 **Authentication**: Firebase Auth with email/password and Google OAuth
- 💬 **AI Chat**: Conversational AI using Google Gemini with context-aware responses
- 📄 **Document Q&A**: Upload documents and ask questions using RAG (Retrieval Augmented Generation)
- 📝 **Resume Analysis**: Analyze resumes against job descriptions with detailed scoring and recommendations
- 🏗️ **Production-Ready**: Clean architecture with dependency injection, decorators, and service layer

## Tech Stack

- **Framework**: FastAPI
- **Database**: Google Cloud Firestore
- **Authentication**: Firebase Admin SDK
- **AI**: Google Gemini 2.5 Flash
- **Vector DB**: FAISS (for document search)
- **Embeddings**: HuggingFace Sentence Transformers
- **Package Manager**: Poetry

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
│   │   │   └── resume.py       # Resume analysis routes
│   ├── core/
│   │   ├── security.py         # Auth utilities
│   │   └── exceptions.py       # Custom exceptions
│   ├── services/
│   │   ├── auth_service.py     # Auth business logic
│   │   ├── chat_service.py     # Chat business logic
│   │   ├── document_service.py # Document processing logic
│   │   └── resume_service.py   # Resume analysis logic
│   ├── models/
│   │   └── schemas.py          # Pydantic models
│   └── db/
│       └── firestore_client.py # Firestore client
├── pyproject.toml              # Poetry configuration
├── .env.example               # Environment variables template
└── README.md
```

## Setup

### Prerequisites

- Python 3.10+
- Poetry
- Firebase project with Firestore enabled
- Google Gemini API key

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

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. **Activate Poetry shell**
```bash
poetry shell
```

6. **Run the application**
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

### Document Chat (`/document`)
- `POST /document/upload` - Upload document for processing
- `GET /document/status` - Check processing status
- `POST /document/ask` - Ask question about document

### Resume (`/resume`)
- `POST /resume/compare-resume-jd` - Analyze resume against job description
- `POST /resume/generate-resume` - Generate/formatted resume JSON

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

## Deployment

The application is configured for deployment on Render (or similar platforms) with:
- `Procfile` for process management
- Environment variable support for Firebase credentials
- CORS configuration for frontend integration

## Architecture Highlights

- **Dependency Injection**: FastAPI's dependency system for auth and database access
- **Decorators**: Custom decorators for error handling and authentication
- **Service Layer**: Business logic separated from route handlers
- **Pydantic Models**: Request/response validation with schemas
- **Configuration Management**: Centralized settings with pydantic-settings

## License

[Your License Here]

