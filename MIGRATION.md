# Migration Guide: Old to New Structure

This document outlines the changes made during the refactoring to a production-ready structure.

## Key Changes

### 1. Package Management
- **Old**: `requirements.txt` with pip
- **New**: `pyproject.toml` with Poetry
- **Action**: Run `poetry install` instead of `pip install -r requirements.txt`

### 2. Project Structure
- **Old**: Flat structure with routes in `app/api/`
- **New**: Organized structure with versioned API (`app/api/v1/`), services, models, and core modules

### 3. Dependency Injection
- **Old**: Manual token verification in each route
- **New**: FastAPI dependency injection via `app/dependencies.py`
- **Example**: 
  ```python
  # Old
  def route(request: Request):
      verify_token(request)
      
  # New
  def route(current_user: dict = Depends(get_current_user)):
      # current_user is already verified
  ```

### 4. Decorators
- **New**: Custom decorators in `app/decorators.py`
- **Usage**: `@handle_exceptions` for error handling

### 5. Service Layer
- **Old**: Business logic mixed with route handlers
- **New**: Separated service layer in `app/services/`
- **Benefits**: Better testability, reusability, and separation of concerns

### 6. Configuration Management
- **Old**: Environment variables accessed directly with `os.getenv()`
- **New**: Centralized settings via `app/config.py` using pydantic-settings

### 7. API Routes
- **Old**: Routes directly in `app/api/auth.py`, `chat.py`, etc.
- **New**: Versioned routes in `app/api/v1/auth.py`, `chat.py`, etc.

## Files Removed
- `app/api/auth.py` (moved to `app/api/v1/auth.py`)
- `app/api/chat.py` (moved to `app/api/v1/chat.py`)
- `app/api/documentchat.py` (moved to `app/api/v1/document.py`)
- `app/api/resumeanalyser.py` (moved to `app/api/v1/resume.py`)
- `requirements.txt` (replaced by `pyproject.toml`)

## Files Added
- `pyproject.toml` - Poetry configuration
- `app/config.py` - Settings management
- `app/dependencies.py` - Dependency injection
- `app/decorators.py` - Route decorators
- `app/core/` - Core utilities (security, exceptions)
- `app/services/` - Business logic layer
- `app/models/schemas.py` - Pydantic models
- `app/api/v1/` - Versioned API routes

## Environment Variables
No changes to environment variable names, but they're now managed through `app/config.py`.

## API Endpoints
All endpoints remain the same - no breaking changes to the API contract.

## Next Steps
1. Install Poetry: `curl -sSL https://install.python-poetry.org | python3 -`
2. Install dependencies: `poetry install`
3. Update `.env` file if needed
4. Test the application: `poetry run uvicorn app.main:app --reload`

