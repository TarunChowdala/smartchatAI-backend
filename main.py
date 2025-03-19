from fastapi import FastAPI
from sqlalchemy import text
from database import engine, SessionLocal
from models import Base
import routes
from contextlib import asynccontextmanager

# Define startup and shutdown events using lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting application...")

    # Create database tables
    Base.metadata.create_all(bind=engine)

    # Test database connection
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))  # ✅ Fix: Use text() explicitly
        print("✅ Database connection successful!")
    except Exception as e:
        print("❌ Database connection failed:", e)
    finally:
        db.close()

    yield  # Continue running the application

    print("🛑 Shutting down application...")

# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Include API routes
# app.include_router(routes.router)

# Home route
@app.get("/")
def home():
    return {"message": "Welcome to the AI Chat API"}
