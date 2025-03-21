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
from database.models import get_database

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")
CORS(chat_bp, supports_credentials=True)

nltk.download("punkt")
nltk.download('punkt_tab')
nltk.download("stopwords")


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
        "title": "New Session",
        "messages": []
    }
    chat_history_collection.insert_one(session_data)

    print(f"Created new session: {session_id}")  # Debug
    return jsonify({"session_id": session_id, "session_title": "New Session"}), 201

@chat_bp.route("/start_intro", methods=["POST"])
def start_intro():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401

    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # Check if intro session already exists
    session = chat_history_collection.find_one({"user_id": ObjectId(user_id), "title": "Introduction Session"})
    if session:
        return jsonify({"session_id": session["session_id"]}), 200

    # Create a new introduction session
    session_id = str(uuid.uuid4())
    chat_history_collection.insert_one({
        "session_id": session_id,
        "user_id": ObjectId(user_id),
        "title": "Introduction Session",
        "messages": [
            {"role": "AI", "content": "Hello! I'm AIRA. Let's get to know each other. What's your name?", "created_at": time.time()}
        ],
        "created_at": time.time(),
    })

    return jsonify({"session_id": session_id}), 200

@chat_bp.route("/follow_up", methods=["GET"])
def follow_up():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401

    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    db = get_database()
    users_collection = db["users"]
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user or not user.get("profile_completed"):
        return jsonify({"error": "Profile not found"}), 400

    name = user.get("name", "friend")
    greeting = f"Hey {name}, how's it going today? 😊"
    
    return jsonify({"message": greeting}), 200


@chat_bp.route("/send", methods=["POST"])
def chat():
    """Handle sending a message and updating the session title based on AIRA's response."""

    # Authentication (assumed)
    print("Send api")
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    print("User Id : ",user_id)
    # Parse request
    data = request.get_json()
    user_input = data.get("message", "").strip()
    session_id = data.get("session_id")
    if not user_input or not session_id:
        return jsonify({"error": "Message and session ID required"}), 400
    print("user input : ",user_input)
    # Find session
    session = chat_history_collection.find_one({"session_id": session_id, "user_id": ObjectId(user_id)})
    if not session:
        return jsonify({"error": "Session not found or access denied"}), 403

    # Generate AI response
    response_data = generate_ai_response(user_input, session_id)

    # Debugging response_data
    print("Full response_data:", response_data)  # Check full structure

    # Ensure response_data is a dict and contains 'message'
    if isinstance(response_data, dict) and "message" in response_data:
        ai_response = response_data["message"].strip()
    else:
        ai_response = ""  # Fallback if key is missing

    print("ai_response:", ai_response)  # Debugging

    # Update title if it's the first message
    messages = session.get("messages", [])
    if len(messages) == 0 and ai_response:
        new_title = generate_title(ai_response)  # Use AIRA's response for title
        print("\n\n\nNew title:", new_title)  # Debugging
        chat_history_collection.update_one(
            {"session_id": session_id},
            {"$set": {"title": new_title}}
        )
        session_title = new_title
    else:
        session_title = session.get("title", "New Session")

    return jsonify({**response_data, "session_title": session_title}), 200


def generate_title(message):
    """Generate a dynamic session title based on important words from AIRA's response."""
    
    # Tokenize words and remove stopwords
    stop_words = set(stopwords.words('english'))
    words = word_tokenize(message)
    filtered_words = [word for word in words if word.lower() not in stop_words and word.isalnum()]
    
    # Get most frequent words
    word_counts = Counter(filtered_words)
    important_words = [word for word, _ in word_counts.most_common(5)]  # Top 5 words
    
    # Join to form a title
    return " ".join(important_words).title() if important_words else "New Session"

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