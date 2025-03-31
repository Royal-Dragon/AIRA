from flask import Blueprint, request, jsonify
from flask_cors import CORS
from functions.feedback_functions import (
    get_user_id_from_token,
    get_feedback_collection,
    validate_feedback_data,
    get_user_feedback,
    update_user_feedback,
    handle_like_dislike,
    handle_comment,
    get_remembered_messages,
    handle_daily_reminder,
    handle_personal_info_or_goals,
    get_daily_feedback_collection,
    validate_daily_feedback_data,
    insert_daily_feedback,
    clean_expired_reminders
)
from utils import get_session_id
import logging

feedback_bp = Blueprint("feedback", __name__, url_prefix="/api/feedback")
logger = logging.getLogger(__name__)

CORS(feedback_bp, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5173"}})

@feedback_bp.route("/submit", methods=["POST"])
def submit_feedback():
    """Submit structured feedback for chatbot responses."""
    if not request.json:
        logger.warning("No JSON data provided in request")
        return jsonify({"error": "No data provided"}), 400

    user_id, error = get_user_id_from_token(request)
    if error:
        return error

    data = request.json
    is_valid, error = validate_feedback_data(data)
    if not is_valid:
        return error

    feedback_type = data.get("feedback_type")
    response_id = data.get("response_id")
    comment = data.get("comment", "").strip()

    # Get user messages for the response
    user_message, aira_response, error = get_remembered_messages(user_id, response_id)
    if error:
        return error

    # Handle different feedback types
    if feedback_type in ["like", "dislike"]:
        feedback_collection = get_feedback_collection()
        user_feedback = get_user_feedback(feedback_collection, user_id)
        handle_like_dislike(user_feedback, response_id, feedback_type)
        success, error = update_user_feedback(feedback_collection, user_id, user_feedback)
    
    elif feedback_type == "comment":
        feedback_collection = get_feedback_collection()
        user_feedback = get_user_feedback(feedback_collection, user_id)
        handle_comment(user_feedback, response_id, comment)
        success, error = update_user_feedback(feedback_collection, user_id, user_feedback)
    
    elif feedback_type == "daily_reminders":
        feedback_collection = get_feedback_collection()
        user_feedback = get_user_feedback(feedback_collection, user_id)
        handle_daily_reminder(user_feedback, response_id, user_message, aira_response)
        success, error = update_user_feedback(feedback_collection, user_id, user_feedback)
    
    elif feedback_type in ["goals", "personal_info"]:
        success, error = handle_personal_info_or_goals(
            user_id, response_id, user_message, aira_response, feedback_type
        )
    
    else:
        success = False
        error = (jsonify({"error": "Unknown feedback type"}), 400)

    if not success:
        return error

    return jsonify({"message": "Feedback recorded successfully"}), 200

@feedback_bp.route("/daily", methods=["POST"])
def submit_daily_feedback():
    """Submit daily feedback for chatbot sessions."""
    if not request.json:
        logger.warning("No JSON data provided in request")
        return jsonify({"error": "No data provided"}), 400

    user_id, error = get_user_id_from_token(request)
    if error:
        return error

    session_id = get_session_id(request)
    if not session_id:
        return jsonify({"error": "Invalid session"}), 400

    data = request.json
    is_valid, error = validate_daily_feedback_data(data, session_id)
    if not is_valid:
        return error

    rating = data.get("rating")
    comment = data.get("comment", "")

    daily_feedback_collection = get_daily_feedback_collection()
    success, error = insert_daily_feedback(
        daily_feedback_collection, user_id, session_id, rating, comment
    )
    if not success:
        return error

    return jsonify({"message": "Daily feedback recorded successfully"}), 200

@feedback_bp.route("/clean-reminders", methods=["POST"])
def clean_reminders():
    """Endpoint to manually trigger cleanup of expired reminders."""
    user_id, error = get_user_id_from_token(request)
    if error:
        return error
        
    success = clean_expired_reminders()
    if not success:
        return jsonify({"error": "Failed to clean expired reminders"}), 500
        
    return jsonify({"message": "Expired reminders cleaned successfully"}), 200