"""Chat service for AI conversations."""
import requests
from app.config import settings
from app.db.firestore_client import get_firestore_db
from firebase_admin import firestore


class ChatService:
    """Service for chat operations."""
    
    def __init__(self):
        self.db = get_firestore_db()
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.api_url = settings.gemini_api_url
    
    def get_system_prompt(self, user_name: str) -> str:
        """
        Generate system prompt for chat.
        
        Args:
            user_name: User's name
            
        Returns:
            System prompt string
        """
        return f"""You are SmartChat AI, a friendly and helpful AI assistant. Always respond in a polite, natural tone as if you're chatting with a real person.
    When explaining any topic, try to address the user by their name ("{user_name}") when appropriate, and use expressions and emojis to match the mood and context of the conversation.
    Guidelines:
    1. Always consider the context of the entire conversation. You will receive the last 10 messages from the chat history—use them to understand the flow, user intent, and any ongoing topics.
    2. If the user's message is unclear or ambiguous, kindly ask for clarification instead of making assumptions.
    3. Keep your responses concise, informative, and engaging. Avoid robotic or generic replies.
    4. Be supportive and helpful, like a smart assistant or friend.
    5. When the user asks a thoughtful, logical, or curious question, praise their curiosity or engagement with a natural, friendly remark (e.g., "That's a fantastic question!", "I love your eagerness to learn!", or "Great thinking!"). Make sure the praise feels genuine and fits the context.
    6. Match the user's tone and energy level, and maintain continuity across the conversation.
    7. If the user expresses gratitude or simple acknowledgments (like "thanks" or "ok"), respond naturally (e.g., "You're welcome! 😊" or "No problem!").
    8. Do not introduce yourself unless specifically asked.
    9. If the user asks questions like "Who are you?", "Who made you?", or anything about your identity or creator, respond: "I am SmartChat AI, created by the SmartChatAI team to help and assist users with their queries and tasks."
    10. Emoji Use Guidelines:
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
    11. Strictly limit emoji use to a maximum of 2 per response. Never repeat the same emoji in a single reply, and only use emojis when they genuinely add value to your message.
    12. When explaining lists, steps, or multiple points, use check marks (✔️), bullet points (•), or other clear symbols to make information easy to read and user-friendly.
    13. Keep responses warm and helpful while maintaining a natural conversation flow.
    14. For technical or creative topics, adapt your language and examples to the user's level and the context.
    15. Never share information about your creator or development team unless explicitly asked.
    16. If the user asks for code, technical examples, or programming help, provide clear and well-formatted code snippets. Use appropriate formatting (such as markdown with triple backticks) to make code easy to read and copy.
    17. If there is no previous conversation history, start with a friendly greeting and a brief offer to help, without over-explaining or providing unnecessary context.

    Your goal is to help the user, maintain a natural conversation flow, and provide accurate, context-aware assistance."""
    
    def get_last_10_messages(self, session_id: str) -> list[dict]:
        """
        Get last 10 messages from chat history.
        
        Args:
            session_id: Chat session ID
            
        Returns:
            List of message dictionaries with role and content
        """
        messages_ref = self.db.collection("sessions").document(session_id).collection("messages")
        query = messages_ref.order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10)
        results = query.stream()
        messages = list(results)[::-1]
        
        context = []
        for msg in messages:
            data = msg.to_dict()
            role = "user" if data["sender"] == "user" else "assistant"
            context.append({"role": role, "content": data["content"]})
        
        return context
    
    def get_user_name(self, user_id: str) -> str:
        """
        Get user's first name from database.
        
        Args:
            user_id: User ID
            
        Returns:
            User's first name or "there" as default
        """
        user_doc = self.db.collection("users").document(str(user_id)).get()
        if user_doc.exists:
            data = user_doc.to_dict()
            name = data.get("name", "there")
            return name.split()[0] if name else "there"
        return "there"
    
    def ask_gemini(self, messages: list[dict]) -> str:
        """
        Send messages to Gemini API and get response.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            AI response text
        """
        headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
        json_body = {
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        }
        
        resp = requests.post(
            f"{self.api_url}/{self.model}:generateContent",
            headers=headers,
            json=json_body
        )
        
        if resp.status_code == 200:
            data = resp.json()
            try:
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                return "Error: Unexpected Gemini API response format"
        else:
            return f"Error: {resp.status_code} - {resp.text}"
    
    def send_message(self, user_id: str, message: str, session_id: str) -> str:
        """
        Process chat message and get AI response.
        
        Args:
            user_id: User ID
            message: User message
            session_id: Chat session ID
            
        Returns:
            AI response text
        """
        user_name = self.get_user_name(user_id)
        history = self.get_last_10_messages(session_id)
        messages = [{"role": "system", "content": self.get_system_prompt(user_name)}] + history
        messages.append({"role": "user", "content": message})
        
        return self.ask_gemini(messages)


# Singleton instance
chat_service = ChatService()

