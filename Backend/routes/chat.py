from flask import Blueprint, request, jsonify
import time
from routes.auth import verify_jwt_token
from database.models import chat_history_collection, get_collection
import logging
from bson import ObjectId
from flask_cors import CORS
from functions.chat_functions import (
    generate_ai_response,
    extract_user_info,
    generate_title
)
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Blueprint and CORS
chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")
CORS(chat_bp, supports_credentials=True)

# Access brain_collection for storing user data
brain_collection = get_collection("aira_brain")

# Constants for auto-deletion
AUTO_DELETE_DAYS = 30  # Number of days after which to delete inactive sessions

@chat_bp.route("/new_session", methods=["POST"])
def new_session():
    """Create a new chat session embedded in the user's document."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401

    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user_id_obj = ObjectId(user_id)
    current_time = time.time()
    session_id = str(ObjectId())
    new_session = {
        "session_id": session_id,
        "title": "New Session",
        "messages": [],
        "created_at": current_time,
        "last_active": current_time
    }

    # Find or create user document
    user_doc = chat_history_collection.find_one({"user_id": user_id_obj})
    if not user_doc:
        chat_history_collection.insert_one({"user_id": user_id_obj, "sessions": [new_session]})
    else:
        chat_history_collection.update_one(
            {"user_id": user_id_obj},
            {"$push": {"sessions": new_session}}
        )

    logger.info(f"Created new session: {session_id} for user: {user_id}")
    return jsonify({"session_id": session_id, "session_title": "New Session"}), 201


@chat_bp.route("/start_intro", methods=["POST"])
def start_intro():
    """Start or resume an introduction session embedded in the user's document."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401

    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user_id_obj = ObjectId(user_id)
    user_doc = chat_history_collection.find_one({"user_id": user_id_obj})

    # Check for existing intro session
    if user_doc and "sessions" in user_doc:
        for session in user_doc["sessions"]:
            if session["title"] == "Introduction Session":
                first_message = session["messages"][0]["content"] if session["messages"] else ""
                return jsonify({
                    "session_id": session["session_id"],
                    "message": first_message
                }), 200

    # Create new introduction session
    session_id = str(ObjectId())
    current_time = time.time()
    first_message = "Hey there! 😊 I'm AIRA. I'd love to get to know you better. What's your name?"
    new_session = {
        "session_id": session_id,
        "title": "Introduction Session",
        "messages": [{"role": "AI", "content": first_message, "created_at": current_time}],
        "created_at": current_time,
        "last_active": current_time,
        "current_field": "name"
    }

    if not user_doc:
        chat_history_collection.insert_one({"user_id": user_id_obj, "sessions": [new_session]})
    else:
        chat_history_collection.update_one(
            {"user_id": user_id_obj},
            {"$push": {"sessions": new_session}}
        )

    logger.info(f"Started introduction session: {session_id} for user: {user_id}")
    return jsonify({"session_id": session_id, "message": first_message}), 200


@chat_bp.route("/send", methods=["POST"])
def chat():
    """Handle message sending in a session embedded in the user's document."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    user_input = data.get("message", "").strip()
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "Session ID required"}), 400

    user_id_obj = ObjectId(user_id)
    user_doc = chat_history_collection.find_one({"user_id": user_id_obj})
    if not user_doc or "sessions" not in user_doc:
        return jsonify({"error": "No sessions found for user"}), 403

    # Find session
    session = next((s for s in user_doc["sessions"] if s["session_id"] == session_id), None)
    if not session:
        return jsonify({"error": "Session not found or access denied"}), 403

    current_time = time.time()
    messages = session.get("messages", [])
    brain_fields = ["name", "sex", "age", "height", "weight", "habits", "interests"]
    questions = [
        "Hey there! 😊 I'm AIRA. I'd love to get to know you better. What's your name?",
        "Great! How do you identify? (Male, Female, or Other)",
        "Awesome! How old are you?",
        "Got it! How tall are you? You can share in cm or feet.",
        "And what's your weight? You can tell me in kg or lbs—whichever you prefer!",
        "Nice! Can you tell me about some of your daily habits?",
        "Lastly, what are some things you love doing? Any hobbies or interests?"
    ]

    if session["title"] == "Introduction Session":
        user_data = brain_collection.find_one({"user_id": user_id_obj}) or {}
        current_field = session.get("current_field")

        if current_field is None:
            for field in brain_fields:
                if field not in user_data:
                    current_field = field
                    break
            else:
                current_field = None

        if current_field:
            question_index = brain_fields.index(current_field)
            question = questions[question_index]

            if not user_input:
                ai_response = question
            else:
                extracted_value = extract_user_info(user_input, current_field)
                if extracted_value:
                    brain_collection.update_one(
                        {"user_id": user_id_obj},
                        {"$set": {current_field: extracted_value}},
                        upsert=True
                    )
                    updated_user_data = brain_collection.find_one({"user_id": user_id_obj})
                    next_field = None
                    for field in brain_fields[question_index + 1:]:
                        if field not in updated_user_data:
                            next_field = field
                            break
                    if next_field:
                        ai_response = f"Got it! {questions[brain_fields.index(next_field)]}"
                        session["current_field"] = next_field
                    else:
                        ai_response = "Thanks for sharing! 😊 Now we can have a more personalized conversation tailored just for you! For further conversation start a new session."
                        session["current_field"] = None
                else:
                    ai_response = f"I didn't quite get that. {question}"

            if user_input:
                messages.append({"role": "User", "content": user_input, "created_at": current_time})
            messages.append({"role": "AI", "content": ai_response, "created_at": current_time})
            session["messages"] = messages
            session["last_active"] = current_time

            chat_history_collection.update_one(
                {"user_id": user_id_obj},
                {"$set": {"sessions": user_doc["sessions"]}}
            )
            return jsonify({"message": ai_response, "session_title": "Introduction Session"}), 200

        if not user_input:
            return jsonify({
                "message": "Introduction complete. You can now start chatting.",
                "session_title": "Introduction Session"
            }), 200

    if not user_input:
        return jsonify({"error": "Message required for normal chat"}), 400

    # MODIFIED: Generate AI response but don't let it create a new session
    response_data = generate_ai_response(user_input, session_id, user_id, create_session=False)
    # print("\n\n RESPONSE FROM SEND ROUTE : ",response_data)
    ai_response = response_data.get("message", "").strip() if isinstance(response_data, dict) else ""
    ai_response_id = response_data.get("response_id", "").strip() if isinstance(response_data, dict) else ""
    # print("\n\n AI RESPONSE FROM SEND ROUTE : ",ai_response)
    is_first_message = len(messages) == 0
    if user_input:
        messages.append({"role": "User", "content": user_input, "created_at": current_time})
    messages.append({"role": "AI","response_id":ai_response_id, "content": ai_response, "created_at": current_time})

    new_title = session["title"]
    if is_first_message and ai_response and session["title"] != "Introduction Session":
        new_title = generate_title(ai_response)
        logger.info(f"New title generated for session {session_id}: {new_title}")

    session["messages"] = messages
    session["title"] = new_title
    session["last_active"] = current_time

    chat_history_collection.update_one(
        {"user_id": user_id_obj},
        {"$set": {"sessions": user_doc["sessions"]}}
    )
    return jsonify({**response_data, "session_title": new_title}), 200


@chat_bp.route("/history", methods=["GET"])
def chat_history():
    """Retrieve message history for a specific session embedded in the user's document."""
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

    user_id_obj = ObjectId(user_id)
    user_doc = chat_history_collection.find_one({"user_id": user_id_obj})
    if not user_doc or "sessions" not in user_doc:
        return jsonify({"error": "No sessions found for user"}), 403

    session = next((s for s in user_doc["sessions"] if s["session_id"] == session_id), None)
    if not session:
        return jsonify({"error": "Session not found or access denied"}), 403

    return jsonify({
        "history": session.get("messages", []),
        "title": session.get("title", "New Session")
    }), 200


@chat_bp.route("/sessions", methods=["GET"])
def get_sessions():
    """List all chat sessions embedded in the user's document."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401

    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    user_id_obj = ObjectId(user_id)
    user_doc = chat_history_collection.find_one({"user_id": user_id_obj})
    if not user_doc or "sessions" not in user_doc:
        return jsonify({"sessions": []}), 200

    formatted_sessions = [
        {"session_id": session["session_id"], "session_title": session["title"]}
        for session in sorted(user_doc["sessions"], key=lambda x: x["last_active"], reverse=True)
    ]
    return jsonify({"sessions": formatted_sessions}), 200


@chat_bp.route("/cleanup", methods=["POST"])
def cleanup_old_sessions():
    """Clean up old sessions based on the AUTO_DELETE_DAYS setting."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401

    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user_id_obj = ObjectId(user_id)
    cutoff_time = time.time() - (AUTO_DELETE_DAYS * 24 * 60 * 60)
    
    user_doc = chat_history_collection.find_one({"user_id": user_id_obj})
    if not user_doc or "sessions" not in user_doc:
        return jsonify({"message": "No sessions to clean up"}), 200
    
    # Keep introduction session and sessions active after the cutoff time
    active_sessions = []
    for session in user_doc["sessions"]:
        if session["title"] == "Introduction Session" or session["last_active"] >= cutoff_time:
            active_sessions.append(session)
    
    deleted_count = len(user_doc["sessions"]) - len(active_sessions)
    
    if deleted_count > 0:
        chat_history_collection.update_one(
            {"user_id": user_id_obj},
            {"$set": {"sessions": active_sessions}}
        )
        logger.info(f"Cleaned up {deleted_count} old sessions for user: {user_id}")
    
    return jsonify({"message": f"Cleaned up {deleted_count} old sessions"}), 200
