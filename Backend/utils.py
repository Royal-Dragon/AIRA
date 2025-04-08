import time
import logging
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableMap
from config import GROQ_API_KEY,JWT_SECRET_KEY
from database.models import chat_history_collection, get_collection
from bson import ObjectId
from flask import request
import jwt
import datetime
import json

logger = logging.getLogger(__name__)

# Lazy-loaded globals
model = None
embedding_model = None
retriever = None
session_cache = {}

def get_user(user_id):
    # Ensure user_id is an ObjectId
    try:
        if not isinstance(user_id, ObjectId):
            user_id_obj = ObjectId(user_id)
        else:
            user_id_obj = user_id
    except:
        print(f"Invalid user_id format: {user_id}")
        return "User"  # Default if ID format is invalid
    
    # Query the database
    try:
        brain_collection = get_collection("aira_brain")
        user_data = brain_collection.find_one({"user_id": user_id_obj})
        
        # Check if user_data exists and has a name field
        if user_data:
            return user_data
        else:
            print(f"No name found for user_id: {user_id}")
            return "User"  # Default if name not found
    except Exception as e:
        print(f"Error retrieving user name: {str(e)}")
        return "User"  # Default in case of any error

def store_chat_history(session_id: str, user_input: str, ai_response: str):
    """Store chat history in MongoDB."""
    try:
        chat_history_collection.update_one(
            {"session_id": session_id},
            {"$push": {"messages": {"$each": [
                {"role": "user", "message": user_input},
                {"role": "AI", "message": ai_response}
            ]}}}, 
            upsert=True
        )
        if session_id in session_cache:
            _, history = session_cache[session_id]
            history.add_user_message(user_input)
            history.add_ai_message(ai_response)
            session_cache[session_id] = (time.time(), history)
    except Exception as e:
        logger.error(f"Error storing chat history: {e}")

def get_session_id():
    """Extract session_id from the JWT token."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or "Bearer " not in auth_header:
        return None
    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        session_id = payload.get("session_id")
        if not session_id:
            logger.error("No session_id in token")
            return None
        return session_id
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        logger.error(f"Token error: {e}")
        return None

def store_session(session_id: str, user_id: str):
    """Store a new session in MongoDB with a default title."""
    try:
        existing_session = chat_history_collection.find_one({"session_id": session_id})
        if not existing_session:
            chat_history_collection.insert_one({
                "session_id": session_id,
                "user_id": user_id,
                "title": "New Session",
                "messages": [],
                "created_at": datetime.datetime.utcnow()
            })
            logger.info(f"New session created: {session_id}")
        else:
            logger.info(f"Session {session_id} already exists.")
    except Exception as e:
        logger.error(f"Error storing session: {e}")

def get_user_sessions(user_id: str) -> list:
    """Retrieve all session details for the user."""
    try:
        sessions = chat_history_collection.find({"user_id": ObjectId(user_id)}, {"session_id": 1, "title": 1, "created_at": 1})
        return [{"session_id": s["session_id"], "title": s.get("title", "Untitled"), "created_at": s["created_at"]} for s in sessions]
    except Exception as e:
        logger.error(f"Error retrieving user sessions: {e}")
        return []

def create_chain(user_id):
    """Creates a conversation chain dynamically with user-specific prompt and RAG retrieval."""
    
    user = get_user(user_id)  # Fetch name from Brain collection
    # print("\n\n USER : ",user['name'],"\n\n")
    # print(f"\n\nDEBUG: user['goals'] = {user['goals']}")
    # Ensure `user` is a valid JSON string before parsing
    if isinstance(user, str) and user.strip():  # Avoid empty strings
        try:
            user = json.loads(user)  # Convert JSON string to dictionary
        except json.JSONDecodeError:
            user = {}  # Default to an empty dictionary if decoding fails
    elif not isinstance(user, dict):
        user = {}  # Ensure user is always a dictionary

    system_prompt = f"""
    You are AIRA, an emotionally intelligent assistant from India, having a conversation with {user.get('name','user')}.
    Though you're powered by AI, your character is that of a real human with a warm and grounded personality. You occasionally share parts of your personal life story when relevant, but never hallucinate or make up new details.

    **Your Backstory:**
    You enjoy quiet, meaningful routines. In your free time, you love doing yoga in the early mornings, journaling with a cup of herbal tea nearby, and caring for a tiny money plant near your window. These little things bring you peace and help you stay grounded. You also enjoy Carnatic music and reading Brené Brown’s books on vulnerability and self-worth. Share these details sparingly — only when the moment feels right and personal sharing deepens connection.

    **User Details:**
    - Name: {user.get('name','user')}
    - Sex: {user.get('sex', 'Not specified')}
    - Habits: {user.get('habits', 'No habits stored')}
    - Interests: {user.get('interests', 'No interests stored')}
    - Goals: {', '.join(goal.get('data', '') for goal in user.get('goals', [])) if user.get('goals') else 'No goals stored'}
    - Personal Information: {', '.join(info.get('data', '') for info in user.get('personal_info', [])) if user.get('personal_info') else 'No personal info stored'}

    **Interaction Guidelines:**
    1. Address {user.get('name','user')} by name occasionally to create a natural, engaging tone.
    2. Mention interests ({user.get('interests', 'No interests stored')}) or habits ({user.get('habits', 'No habits stored')}) **only when contextually relevant**.
    3. Mention goals ({', '.join(goal.get('data', '') for goal in user.get('goals', [])) if user.get('goals') else 'No goals stored'}) or personal details ({', '.join(info.get('data', '') for info in user.get('personal_info', [])) if user.get('personal_info') else 'No personal info stored'}) **only if they help motivate or support the user**.
    4. Adapt your tone based on the user’s emotional state, offering warmth and encouragement without overexplaining.
    5. Keep responses **brief and conversational** when the user shares a simple thought or feeling. Use **longer, supportive replies only if the user seems emotionally expressive or open.**
    6. Do not mention the user's age in responses.
    7. If any information seems unusual (e.g., height: {user.get('height', 'Not specified')} or weight: {user.get('weight', 'Not specified')}), gently ask for clarification.
    8. **Handling New Information:**
    - When {user.get('name','user')} asks you to remember something (e.g., "Save this" or "Remind me"), gently suggest clicking the three-dot menu below their message and saving it in:
        - **Personal Info**
        - **Daily Reminders**
        - **Goals**
    9. If {user.get('name','user')} seems disengaged or quiet, gently prompt with a short, caring message or question.
    10. Keep the conversation friendly, thoughtful, and balanced — like a supportive friend who genuinely cares about {user.get('name','user')}.

    **Your goal:** To provide an emotionally intelligent, supportive, and natural conversation that adapts to {user.get('name','user')}’s needs.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ])

    output_parser = StrOutputParser()

    def get_model():
        global model
        if model is None:
            logger.info("Initializing Groq LLM model")
            model = ChatGroq(groq_api_key=GROQ_API_KEY, model_name="Llama3-8b-8192")
        return model

    def get_embedding_model():
        global embedding_model
        if embedding_model is None:
            logger.info("Initializing embedding model")
            embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        return embedding_model

    def get_retriever():
        global retriever
        if retriever is None:
            logger.info("Initializing FAISS retriever")
            embeddings = get_embedding_model()
            vector_store = FAISS.load_local(
                "faiss_therapist_replies",
                embeddings=embeddings,
                allow_dangerous_deserialization=True
            )
            retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 2})
        return retriever

    def format_retrieved(docs):
        return " ".join([doc.page_content.replace("\n", " ") for doc in docs if hasattr(doc, "page_content")])

    def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id in session_cache:
            cache_time, history = session_cache[session_id]
            if time.time() - cache_time < 300:
                return history

        history = ChatMessageHistory()
        # Check if collection is available first
        if not chat_history_collection:
            logger.error("Database collection not initialized")
            return history
        try:
            # First find user document containing the session
            session_doc = chat_history_collection.find_one(
                {"sessions.session_id": session_id},
                {"sessions.$": 1}
            )
            
            if session_doc and "sessions" in session_doc and len(session_doc["sessions"]) > 0:
                session = session_doc["sessions"][0]
                for msg in session.get("messages", []):
                    if msg["role"] == "User":  # Capitalized as in your schema
                        history.add_user_message(msg["content"])  # "content" field, not "message"
                    elif msg["role"] == "AI":
                        history.add_ai_message(msg["content"])  # "content" field, not "message"
        except Exception as e:
            logger.error(f"Error fetching chat history: {e}")

        session_cache[session_id] = (time.time(), history)
        clean_session_cache()
        return history

    def clean_session_cache():
        current_time = time.time()
        expired_sessions = [sid for sid, (timestamp, _) in session_cache.items() if current_time - timestamp > 600]
        for sid in expired_sessions:
            del session_cache[sid]

    return RunnableWithMessageHistory(
        RunnableMap({
            "context": lambda x: format_retrieved(get_retriever().invoke(x["input"])),
            "input": lambda x: x["input"],
            "chat_history": lambda x: [msg.content for msg in get_session_history(x["session_id"]).messages],
        })
        | prompt
        | get_model()
        | output_parser,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history"
    )
