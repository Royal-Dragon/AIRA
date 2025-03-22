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
from database.models import chat_history_collection, brain_collection
from bson import ObjectId
from flask import request
import jwt
import datetime

logger = logging.getLogger(__name__)

# Lazy-loaded globals
model = None
embedding_model = None
retriever = None
session_cache = {}

def get_user_name(user_id):
    """Fetch user name from Brain collection."""
    user_data = brain_collection.find_one({"user_id": ObjectId(user_id)}, {"name": 1})
    return user_data["name"] if user_data else "User"

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
    
    user_name = get_user_name(user_id)  # Fetch name from Brain collection
    system_prompt = f"You are AIRA, an AI assistant. You are talking to {user_name}. Engage in meaningful conversations and remember key details about the user. Keep your responses clear, concise, and engaging."

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
        try:
            session = chat_history_collection.find_one({"session_id": session_id})
            if session:
                for msg in session.get("messages", []):
                    if msg["role"] == "user":
                        history.add_user_message(msg["message"])
                    elif msg["role"] == "AI":
                        history.add_ai_message(msg["message"])
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
