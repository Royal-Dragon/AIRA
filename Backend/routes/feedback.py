from flask import Blueprint, request, jsonify
from datetime import datetime
from database.models import get_database
from routes.auth import verify_jwt_token  
from utils import get_session_id
import logging
from flask_cors import CORS

feedback_bp = Blueprint("feedback", __name__, url_prefix="/api/feedback")
logger = logging.getLogger(__name__)

CORS(feedback_bp,supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5173"}})

def get_feedback_collections():
    """Retrieve feedback collections dynamically."""
    db = get_database()
    return db["feedback_responses"], db["daily_feedback"]

@feedback_bp.route("/submit", methods=["POST"])
def submit_feedback():
    """Submit structured feedback for chatbot responses."""
    try:
        # Get MongoDB collection
        feedback_collection, _ = get_feedback_collections()

        # Validate Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid Authorization header")
            return jsonify({"error": "Missing or invalid token"}), 401
        
        token = auth_header.split(" ")[1]
        user_id = verify_jwt_token(token)
        if not user_id:
            logger.warning(f"Token verification failed for token: {token}")
            return jsonify({"error": "Unauthorized. Please log in."}), 401

        # Validate request JSON
        if not request.json:
            logger.warning("No JSON data provided in request")
            return jsonify({"error": "No data provided"}), 400
        
        data = request.json
        response_id = data.get("response_id")
        feedback_type = data.get("feedback_type")
        comment = data.get("comment", "").strip()

        # Validate required fields
        valid_feedback_types = ["like", "dislike", "comment"]
        if not response_id or feedback_type not in valid_feedback_types:
            logger.warning(f"Invalid feedback data: response_id={response_id}, feedback_type={feedback_type}")
            return jsonify({
                "error": "Invalid feedback data",
                "details": "response_id and feedback_type ('like', 'dislike', 'comment') are required."
            }), 400

        feedback_filter = {"user_id": user_id, "response_id": response_id}

        # Handle Like & Dislike
        if feedback_type in ["like", "dislike"]:
            update_data = {
                "feedback_type": feedback_type,
                "timestamp": datetime.utcnow()
            }
            
            if feedback_type == "dislike" and comment:
                # Append comment if provided with dislike
                update_data["comments"] = update_data.get("comments", []) + [
                    {"text": comment, "timestamp": datetime.utcnow()}
                ]
            
            feedback_collection.update_one(
                feedback_filter,
                {"$set": update_data},
                upsert=True
            )

        # Handle Comment
        elif feedback_type == "comment":
            if not comment:
                logger.warning(f"Empty comment for response_id={response_id}")
                return jsonify({
                    "error": "Comment required",
                    "details": "Comment cannot be empty."
                }), 400
            
            feedback_collection.update_one(
                feedback_filter,
                {
                    "$push": {
                        "comments": {"text": comment, "timestamp": datetime.utcnow()}
                    }
                },
                upsert=True
            )

        logger.info(f"Feedback recorded by user {user_id} for response {response_id} ({feedback_type})")
        return jsonify({"message": "Feedback recorded successfully"}), 200

    except ValueError as ve:
        logger.error(f"ValueError in submit_feedback: {str(ve)}")
        return jsonify({"error": "Invalid data format"}), 400
    except pymongo.errors.PyMongoError as pe:
        logger.error(f"MongoDB error in submit_feedback: {str(pe)}")
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        logger.error(f"Unexpected error in submit_feedback: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@feedback_bp.route("/daily_feedback", methods=["POST"])
def submit_daily_feedback():
    """Users provide overall experience feedback at the end of the day."""
    _, daily_feedback_collection = get_feedback_collections()

    user_id = verify_jwt_token(request)
    if not user_id:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    data = request.json
    session_id = get_session_id()
    rating = data.get("rating")
    comment = data.get("comment", "").strip()

    if not session_id or rating is None:
        return jsonify({"error": "Invalid data", "details": "'session_id' and 'rating' are required."}), 400

    if not isinstance(rating, (int, float)) or not (1 <= rating <= 5):
        return jsonify({"error": "Invalid rating", "details": "Rating must be a number between 1 and 5."}), 400

    try:
        daily_feedback_collection.insert_one({
            "user_id": user_id,
            "session_id": session_id,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.utcnow()
        })
        logger.info(f"Daily feedback submitted by user {user_id} for session {session_id}")
    except Exception as e:
        logger.error(f"Database error while submitting daily feedback: {e}")
        return jsonify({"error": "Database error", "details": str(e)}), 500

    return jsonify({"message": "Daily experience feedback submitted successfully"}), 200
