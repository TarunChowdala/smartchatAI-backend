"""Chat service for AI conversations."""
import requests
from app.config import settings
from app.db.firestore_client import get_firestore_db
from firebase_admin import firestore
from app.services.usage_limit_service import usage_limit_service


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
    
    def send_message(self, user_id: str, message: str, session_id: str = None, model_name: str = None) -> dict:
        """
        Process chat message and get AI response.
        
        Args:
            user_id: User ID
            message: User message
            session_id: Chat session ID
            model_name: Optional model name to use
            
        Returns:
            Dictionary with AI response text and session_id
        """
        # Generate session_id if not provided
        if not session_id:
            import uuid
            session_id = str(uuid.uuid4())

        # Check session and message limits
        session_ref = self.db.collection("sessions").document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            # New session - check session count limit
            usage_limit_service.check_session_limit(user_id)
            # Create session document
            session_ref.set({
                "user_id": user_id,
                "model_name": model_name or self.model,
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            })
        else:
            # Existing session - check message count limit
            usage_limit_service.check_message_limit(session_id, user_id)
            # Update session timestamp and optionally model
            update_data = {"updated_at": firestore.SERVER_TIMESTAMP}
            if model_name:
                update_data["model_name"] = model_name
            session_ref.update(update_data)
            
        # Save user message to Firestore
        messages_ref = session_ref.collection("messages")
        messages_ref.add({
            "sender": "user",
            "content": message,
            "user_id": user_id,
            "model_name": model_name or self.model,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

        user_name = self.get_user_name(user_id)
        history = self.get_last_10_messages(session_id)
        messages = [{"role": "system", "content": self.get_system_prompt(user_name)}] + history
        messages.append({"role": "user", "content": message})
        
        reply = self.ask_gemini(messages)
        
        # Save assistant response to Firestore
        messages_ref.add({
            "sender": "assistant",
            "content": reply,
            "user_id": user_id,
            "model_name": model_name or self.model,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        
        return {
            "reply": reply,
            "session_id": session_id
        }
    
    def get_all_sessions(self, user_id: str, limit: int = 50) -> dict:
        """
        Get all sessions for a user.
        
        Args:
            user_id: User ID from token
            limit: Maximum number of sessions to return
            
        Returns:
            List of sessions with metadata
        """
        sessions_ref = self.db.collection("sessions")
        sessions = []
        
        try:
            # Fetch sessions belonging to user without order_by to avoid index requirement
            query = sessions_ref.where("user_id", "==", user_id).limit(limit * 2)
            session_docs = list(query.stream())
            
            # If no results found with user_id field, try fallback filter
            if not session_docs:
                all_sessions = sessions_ref.limit(100).stream()
                for doc in all_sessions:
                    data = doc.to_dict()
                    if data.get("user_id") == user_id:
                        session_docs.append(doc)
        except Exception as e:
            print(f"Error fetching sessions: {e}")
            session_docs = []
            
        # Convert to list of dicts for sorting
        session_list = []
        for doc in session_docs:
            data = doc.to_dict()
            data["session_id"] = doc.id
            session_list.append(data)
            
        # Sort by updated_at (or created_at) DESC (most recent first)
        session_list.sort(key=lambda x: str(x.get('updated_at') or x.get('created_at') or ''), reverse=True)
        
        # Process limited number of sessions and get message counts
        for session_data in session_list[:limit]:
            session_id = session_data["session_id"]
            
            # Get message count efficiently
            messages_ref = self.db.collection("sessions").document(session_id).collection("messages")
            message_count = len(list(messages_ref.stream()))
            
            sessions.append({
                "session_id": session_id,
                "user_id": session_data.get("user_id"),
                "created_at": session_data.get("created_at"),
                "updated_at": session_data.get("updated_at"),
                "message_count": message_count
            })
        
        return {
            "sessions": sessions,
            "count": len(sessions)
        }
    
    def get_session(self, session_id: str, user_id: str) -> dict:
        """
        Get session information.
        
        Args:
            session_id: Session identifier
            user_id: User ID from token (for verification)
            
        Returns:
            Session data
            
        Raises:
            HTTPException: If session not found
        """
        session_ref = self.db.collection("sessions").document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Session not found")
        
        session_data = session_doc.to_dict()
        
        # Get message count
        messages_ref = session_ref.collection("messages")
        message_count = len(list(messages_ref.stream()))
        
        return {
            "session_id": session_id,
            "user_id": session_data.get("user_id"),
            "created_at": session_data.get("created_at"),
            "updated_at": session_data.get("updated_at"),
            "message_count": message_count
        }
    
    def get_messages(self, session_id: str, user_id: str, limit: int = 50) -> dict:
        """
        Get messages for a session.
        
        Args:
            session_id: Session identifier
            user_id: User ID from token (for verification)
            limit: Maximum number of messages to return
            
        Returns:
            Messages list
            
        Raises:
            HTTPException: If session not found
        """
        session_ref = self.db.collection("sessions").document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get messages ordered by timestamp
        messages_ref = session_ref.collection("messages")
        query = messages_ref.order_by("timestamp", direction=firestore.Query.ASCENDING).limit(limit)
        results = query.stream()
        
        messages = []
        for msg in results:
            data = msg.to_dict()
            messages.append({
                "id": msg.id,
                "sender": data.get("sender"),
                "content": data.get("content"),
                "timestamp": data.get("timestamp")
            })
        
        return {
            "session_id": session_id,
            "messages": messages,
            "count": len(messages)
        }
    
    def delete_session(self, session_id: str, user_id: str) -> dict:
        """
        Delete chat session and all its messages.
        
        Args:
            session_id: Session identifier
            user_id: User ID from token (for verification)
            
        Returns:
            Deletion confirmation
            
        Raises:
            HTTPException: If session not found
        """
        session_ref = self.db.collection("sessions").document(session_id)
        session_doc = session_ref.get()
        
        if not session_doc.exists:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Verify ownership if user_id is stored in session
        session_data = session_doc.to_dict()
        if session_data.get("user_id") and session_data.get("user_id") != user_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not authorized to delete this session")
        
        # Delete all messages in subcollection
        messages_ref = session_ref.collection("messages")
        messages = messages_ref.stream()
        deleted_count = 0
        for msg in messages:
            msg.reference.delete()
            deleted_count += 1
        
        # Delete session document
        session_ref.delete()
        
        return {
            "message": "Session deleted successfully",
            "session_id": session_id,
            "messages_deleted": deleted_count
        }


# Singleton instance
chat_service = ChatService()

