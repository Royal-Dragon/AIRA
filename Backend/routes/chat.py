from flask import Blueprint, request, jsonify
import time
import uuid
from utils import create_chain, get_session_history, store_chat_history, get_session_id, get_user_sessions
from routes.auth import verify_jwt_token
from database.models import chat_history_collection
import logging
from bson import ObjectId
import re
from collections import Counter
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk
from flask_cors import CORS

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")
CORS(chat_bp, supports_credentials=True)

nltk.download("punkt")
nltk.download("stopwords")

def extract_keywords(text, max_keywords=5):
    """Extracts important keywords from the given text."""
    stop_words = set(stopwords.words("english"))
    words = word_tokenize(text.lower())
    words = [word for word in words if word.isalnum() and word not in stop_words]
    word_freq = Counter(words)
    keywords = [word for word, _ in word_freq.most_common(max_keywords)]
    return " ".join(keywords).title()

def generate_ai_response(user_input: str, session_id: str) -> dict:
    """Generate AI response and store chat history."""
    chain = create_chain()
    start_time = time.time()
    ai_response = chain.invoke(
        {"input": user_input, "session_id": session_id},
        config={"configurable": {"session_id": session_id}}
    )
    response_time = round(time.time() - start_time, 2)
    response_id = str(uuid.uuid4())

    ai_message = {"role": "AI", "message": ai_response, "response_id": response_id, "created_at": time.time()}
    store_chat_history(session_id, user_input, ai_message)

    session = chat_history_collection.find_one({"session_id": session_id})
    if session and session.get("title") == "New Session":
        title = " ".join(user_input.split()[:5]) + "..."
        chat_history_collection.update_one(
            {"session_id": session_id},
            {"$set": {"title": title}}
        )

    return {"response_id": response_id, "message": ai_response, "response_time": response_time}

@chat_bp.route("/new_session", methods=["POST"])
def new_session():
    """Create a new chat session for the user."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    session_id = str(ObjectId())
    session_data = {
        "session_id": session_id,
        "user_id": ObjectId(user_id),
        "title": "New Session 1",
        "messages": []
    }
    chat_history_collection.insert_one(session_data)

    print(f"Created new session: {session_id}")  # Debug
    return jsonify({"session_id": session_id, "session_title": "New Session"}), 201

@chat_bp.route("/send", methods=["POST"])
def chat():
    """Handle sending a message and updating the session title if it's the first message."""
    # Authentication (assumed)
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # Parse request
    data = request.get_json()
    user_input = data.get("message", "").strip()
    session_id = data.get("session_id")
    if not user_input or not session_id:
        return jsonify({"error": "Message and session ID required"}), 400

    # Find session
    session = chat_history_collection.find_one({"session_id": session_id, "user_id": ObjectId(user_id)})
    if not session:
        return jsonify({"error": "Session not found or access denied"}), 403

    # Update title if first message
    messages = session.get("messages", [])
    if len(messages) == 0:
        new_title = generate_title(user_input)
        chat_history_collection.update_one(
            {"session_id": session_id},
            {"$set": {"title": new_title}}
        )
        session_title = new_title
    else:
        session_title = session.get("title", "New Session")

    # Append message (assume generate_ai_response handles this)
    response_data = generate_ai_response(user_input, session_id)
    return jsonify({**response_data, "session_title": session_title}), 200

def generate_title(message):
    """Generate a title from the message."""
    return message[:30] + "..." if len(message) > 30 else message

@chat_bp.route("/history", methods=["GET"])
def chat_history():
    """Fetch chat history for a specific session."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "Session ID required"}), 400

    try:
        session = chat_history_collection.find_one({"session_id": session_id, "user_id": ObjectId(user_id)})
        if not session:
            return jsonify({"error": "Session not found or access denied"}), 403
        return jsonify({"history": session.get("messages", []), "title": session.get("title", "New Session")}), 200
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        return jsonify({"error": "Internal server error"}), 500

@chat_bp.route("/save_session", methods=["POST"])
def save_session():
    """Saves a session with a generated title."""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        user_id = verify_jwt_token(token)
        if not user_id:
            return jsonify({"error": "Unauthorized. Please log in."}), 401

        # Extract JSON Data from Request
        data = request.get_json()
        session_id = data.get("session_id")
        session_title = data.get("session_title", "New Session")
        messages = data.get("messages", [])

        if not session_id:
            return jsonify({"error": "Missing session_id"}), 400
        
        # Ensure session_id and user_id match a session in DB
        query = {"session_id": session_id, "user_id": ObjectId(user_id)}
        session = chat_history_collection.find_one(query)

        if not session:
            return jsonify({"error": "Session not found"}), 404

        # Extract current messages & session title
        current_title = session.get("title", "New Session")
        title = current_title

        # Auto-generate session title if it's "New Session"
        if current_title == "New Session" and messages:
            for msg in messages:
                if msg.get("sender") == "AIRA":  # Extract keywords from AI response
                    title = extract_keywords(msg["message"])
                    break
            if title == "New Session" and messages:
                title = " ".join(messages[0]["message"].split()[:5]) + "..."

        # Update session title if changed
        if title != current_title:
            chat_history_collection.update_one(
                {"session_id": session_id}, {"$set": {"title": title}}
            )
            print(f"✅ Session {session_id} updated with title: {title}")

        return jsonify({"message": "Session saved successfully", "title": title}), 200

    except Exception as e:
        print(f"❌ Error saving session: {e}")
        return jsonify({"error": "Internal server error"}), 500

@chat_bp.route("/sessions", methods=["GET"])
def get_sessions():
    """Retrieve user chat sessions."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    sessions = chat_history_collection.find({"user_id": ObjectId(user_id)})
    # Ensure sessions is in the correct format: list of dicts with session_id and session_title
    formatted_sessions = [
        {"session_id": session["session_id"], "session_title": session["title"]}
        for session in sessions
    ]
    return jsonify({"sessions": formatted_sessions}), 200