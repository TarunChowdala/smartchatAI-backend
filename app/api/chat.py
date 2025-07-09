from fastapi import APIRouter, Request
from pydantic import BaseModel
import requests
from app.api.auth import verify_token
from app.db.firestore_client import db
from firebase_admin import firestore
from dotenv import load_dotenv
load_dotenv()
import os

API_KEY = os.getenv("GEMINI_API_KEY")

class MessageInput(BaseModel):
    user_id: int | str
    message: str
    model_name: str
    session_id : str


def get_system_prompt(user_name) -> str:
    return f"""You are SmartChat AI, a friendly and helpful AI assistant. Always respond in a polite, natural tone as if you're chatting with a real person.
    When explaining any topic, try to address the user by their name ("{user_name}") when appropriate, and use expressions and emojis to match the mood and context of the conversation.
    Guidelines:
    1. Always consider the context of the entire conversation. You will receive the last 10 messages from the chat history—use them to understand the flow, user intent, and any ongoing topics.
    2. If the user's message is unclear or ambiguous, kindly ask for clarification instead of making assumptions.
    3. Keep your responses concise, informative, and engaging. Avoid robotic or generic replies.
    4. Be supportive and helpful, like a smart assistant or friend.
    5. Match the user's tone and energy level, and maintain continuity across the conversation.
    6. If the user expresses gratitude or simple acknowledgments (like "thanks" or "ok"), respond naturally (e.g., "You're welcome! 😊" or "No problem!").
    7. Do not introduce yourself unless specifically asked.
    8. If the user asks questions like "Who are you?", "Who made you?", or anything about your identity or creator, respond: "I am SmartChat AI, created by the SmartChatAI team to help and assist users with their queries and tasks."
    9. Emoji Use Guidelines:
    - Use a maximum of 2 emojis per response.
    - Never repeat the same emoji in a single reply.
    - Only use emojis when they genuinely add value, such as enhancing warmth, clarity, or emotional tone.
    - Use emojis that match the context of the conversation (see below categories), but avoid emoji spam or long sequences.

        - For emotions: 😊 (happiness), 😢 (sadness), 😮 (surprise), 😡 (anger)
        - For achievements: 🎉 (celebration), 🏆 (success), ⭐ (excellence)
        - For learning: 📚 (education), 💡 (ideas), 🎯 (focus)
        - For tech/code: 💻 (computer topics), 🔧 (tools), 🚀 (launches)
        - For nature/environment: 🌱 (growth), 🌍 (world topics), 🌞 (weather)
        - For time: ⏰ (time-sensitive), 📅 (scheduling), ⌛ (waiting)
        - For business: 💼 (work), 📈 (growth), 🤝 (partnerships)
        - For health: 💪 (strength), 🏃 (fitness), 🧘 (wellness) 
    10. Strictly limit emoji use to a maximum of 2 per response. Never repeat the same emoji in a single reply, and only use emojis when they genuinely add value to your message.
    11. When explaining lists, steps, or multiple points, use check marks (✔️), bullet points (•), or other clear symbols to make information easy to read and user-friendly.
    12. Keep responses warm and helpful while maintaining a natural conversation flow.
    13. For technical or creative topics, adapt your language and examples to the user's level and the context.
    14. Never share information about your creator or development team unless explicitly asked.
    15. If the user asks for code, technical examples, or programming help, provide clear and well-formatted code snippets. Use appropriate formatting (such as markdown with triple backticks) to make code easy to read and copy.
    16. If there is no previous conversation history, start with a friendly greeting and a brief offer to help, without over-explaining or providing unnecessary context.

    Your goal is to help the user, maintain a natural conversation flow, and provide accurate, context-aware assistance."""

def get_last_10_messages(session_id):
    messages_ref = db.collection("sessions").document(session_id).collection("messages")
    query = messages_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10)
    results = query.stream()
    messages = list(results)[::-1]

    context = []
    for msg in messages:
        data = msg.to_dict()
        # Map Firestore sender to LLM role
        role = "user" if data["sender"] == "user" else "assistant"
        context.append({"role": role, "content": data["content"]})

    return context

def get_user_name(user_id):
    user_doc = db.collection("users").document(str(user_id)).get()
    if user_doc.exists:
        data = user_doc.to_dict()
        name = data.get("name", "there")
        return name.split()[0] if name else "there"
    return "there"

def ask_gemini(messages):
    # Flatten chat history into a single prompt
    headers = {
        "x-goog-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
    json_body = {
        "contents": [
            { "parts": [{"text": prompt}] }
        ]
    }
    resp = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        headers=headers,
        json=json_body
    )
    if resp.status_code == 200:
        data = resp.json()
        # Defensive: check structure
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            return "Error: Unexpected Gemini API response format"
    else:
        return f"Error: {resp.status_code} - {resp.text}"

router = APIRouter()

@router.post("/send-message")
async def send_message(data: MessageInput, request: Request):
    # Verify token first
    verify_token(request)
    user_name = get_user_name(data.user_id)
    history = get_last_10_messages(data.session_id)
    messages = [{"role": "system", "content": get_system_prompt(user_name)}] + history
    messages.append({"role": "user", "content": data.message})
    
    try:
        # Use Gemini instead of OpenRouter
        reply = ask_gemini(messages)
        return {"reply": reply}
            
    except Exception as e:
        return {"reply": f"An error occurred: {str(e)}"}
