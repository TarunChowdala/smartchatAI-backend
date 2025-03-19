from pydantic import BaseModel

class MessageCreate(BaseModel):
    user_input: str
    bot_response: str

class MessageResponse(BaseModel):
    id: int
    user_input: str
    bot_response: str

    class Config:
        orm_mode = True  # Allows SQLAlchemy models to work with Pydantic
