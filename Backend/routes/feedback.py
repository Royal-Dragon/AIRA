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
    handle_remember,
    get_daily_feedback_collection,
    validate_daily_feedback_data,
    insert_daily_feedback
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

    feedback_collection = get_feedback_collection()
    user_feedback = get_user_feedback(feedback_collection, user_id)

    if feedback_type in ["like", "dislike"]:
        handle_like_dislike(user_feedback, response_id, feedback_type)
    elif feedback_type == "comment":
        handle_comment(user_feedback, response_id, comment)
    elif feedback_type == "remember":
        user_message, aira_response, error = get_remembered_messages(user_id, response_id)
        if error:
            return error
        handle_remember(user_feedback, response_id, user_message, aira_response)

    success, error = update_user_feedback(feedback_collection, user_id, user_feedback)
    if not success:
        return error

    return jsonify({"message": "Feedback recorded successfully"}), 200

@feedback_bp.route("/daily_feedback", methods=["POST"])
def submit_daily_feedback():
    """Submit daily experience feedback."""
    if not request.json:
        logger.warning("No JSON data provided in request")
        return jsonify({"error": "No data provided"}), 400

    user_id, error = get_user_id_from_token(request)
    if error:
        return error

    data = request.json
    session_id = get_session_id()
    is_valid, error = validate_daily_feedback_data(data, session_id)
    if not is_valid:
        return error

    rating = data.get("rating")
    comment = data.get("comment", "").strip()
    daily_feedback_collection = get_daily_feedback_collection()

    success, error = insert_daily_feedback(daily_feedback_collection, user_id, session_id, rating, comment)
    if not success:
        return error

    return jsonify({"message": "Daily experience feedback submitted successfully"}), 200