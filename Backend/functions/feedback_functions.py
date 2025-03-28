from database.models import get_collection
from bson.objectid import ObjectId
from datetime import datetime
from routes.auth import verify_jwt_token
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

def get_user_id_from_token(request):
    """Verify JWT token from Authorization header and return user ID."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header")
        return None, (jsonify({"error": "Missing or invalid token"}), 401)
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        logger.warning(f"Token verification failed for token: {token}")
        return None, (jsonify({"error": "Unauthorized. Please log in."}), 401)
    return user_id, None

def get_feedback_collection():
    """Retrieve the feedback collection."""
    return get_collection("feedback")

def get_daily_feedback_collection():
    """Retrieve the daily feedback collection."""
    return get_collection("daily_feedback")

def validate_feedback_data(data):
    """Validate feedback submission data."""
    response_id = data.get("response_id")
    feedback_type = data.get("feedback_type")
    comment = data.get("comment", "").strip()
    valid_types = ["like", "dislike", "comment", "remember"]
    if not response_id or feedback_type not in valid_types:
        logger.warning(f"Invalid feedback data: response_id={response_id}, feedback_type={feedback_type}")
        return False, (jsonify({
            "error": "Invalid feedback data",
            "details": "response_id and feedback_type ('like', 'dislike', 'comment', 'remember') are required."
        }), 400)
    if feedback_type == "comment" and not comment:
        return False, (jsonify({"error": "Comment required", "details": "Comment cannot be empty."}), 400)
    return True, None

def get_user_feedback(feedback_collection, user_id):
    """Fetch or initialize user feedback document."""
    user_feedback = feedback_collection.find_one({"_id": ObjectId(user_id)})
    if not user_feedback:
        user_feedback = {"_id": ObjectId(user_id), "feedback": [], "remembered_messages": []}
    return user_feedback

def update_user_feedback(feedback_collection, user_id, user_feedback):
    """Update or insert user feedback in the database."""
    try:
        feedback_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": user_feedback},
            upsert=True
        )
        return True, None
    except Exception as e:
        logger.error(f"Database error in update_user_feedback: {str(e)}")
        return False, (jsonify({"error": "Database error", "details": str(e)}), 500)

def handle_like_dislike(user_feedback, response_id, feedback_type):
    """Handle like or dislike feedback."""
    feedback_entry = next((f for f in user_feedback["feedback"] if f["response_id"] == response_id), None)
    if feedback_entry:
        feedback_entry["feedback_type"] = feedback_type
    else:
        user_feedback["feedback"].append({
            "response_id": response_id,
            "feedback_type": feedback_type,
            "timestamp": datetime.utcnow(),
            "comments": []
        })

def handle_comment(user_feedback, response_id, comment):
    """Handle comment feedback."""
    feedback_entry = next((f for f in user_feedback["feedback"] if f["response_id"] == response_id), None)
    if feedback_entry:
        feedback_entry["comments"].append({"text": comment, "timestamp": datetime.utcnow()})
    else:
        user_feedback["feedback"].append({
            "response_id": response_id,
            "feedback_type": "comment",
            "timestamp": datetime.utcnow(),
            "comments": [{"text": comment, "timestamp": datetime.utcnow()}]
        })

def get_remembered_messages(user_id, response_id):
    """Retrieve user message and AI response for 'remember' feedback."""
    chat_collection = get_collection("chat_history")
    chat_data = chat_collection.find_one({
        "user_id": ObjectId(user_id),
        "messages": {"$elemMatch": {"role": "AI", "message.response_id": response_id}}
    })
    if not chat_data:
        return None, None, (jsonify({"error": "Chat data not found"}), 404)
    user_message = None
    aira_response = None
    for i in range(len(chat_data["messages"])):
        msg = chat_data["messages"][i]
        if msg["role"] == "AI" and isinstance(msg["message"], dict):
            if msg["message"].get("response_id") == response_id:
                if i > 0 and chat_data["messages"][i - 1]["role"] == "user":
                    user_message = chat_data["messages"][i - 1]["message"]
                aira_response = msg["message"]["message"]
                break
    if not user_message or not aira_response:
        return None, None, (jsonify({"error": "Incomplete chat data"}), 400)
    return user_message, aira_response, None

def handle_remember(user_feedback, response_id, user_message, aira_response):
    """Handle 'remember' feedback by storing messages."""
    user_feedback["remembered_messages"].append({
        "response_id": response_id,
        "user_message": user_message,
        "aira_response": aira_response,
        "timestamp": datetime.utcnow()
    })

def validate_daily_feedback_data(data, session_id):
    """Validate daily feedback submission data."""
    rating = data.get("rating")
    if not session_id or rating is None:
        return False, (jsonify({"error": "Invalid data", "details": "'session_id' and 'rating' are required."}), 400)
    if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
        return False, (jsonify({"error": "Invalid rating", "details": "Rating must be a number between 1 and 5."}), 400)
    return True, None

def insert_daily_feedback(daily_feedback_collection, user_id, session_id, rating, comment):
    """Insert daily feedback into the database."""
    try:
        daily_feedback_collection.insert_one({
            "user_id": user_id,
            "session_id": session_id,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.utcnow()
        })
        logger.info(f"Daily feedback submitted by user {user_id} for session {session_id}")
        return True, None
    except Exception as e:
        logger.error(f"Database error in insert_daily_feedback: {str(e)}")
        return False, (jsonify({"error": "Database error", "details": str(e)}), 500)