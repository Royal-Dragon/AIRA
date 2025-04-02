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
    handle_personal_info_or_goals,
    get_daily_feedback_collection,
    validate_daily_feedback_data,
    insert_daily_feedback,
    clean_expired_reminders,
    get_reminder_collection
)
from utils import get_session_id
import logging
from memory_functions import get_user_reminders,get_valid_reminders,format_reminders_message
from model_memory import extract_reminder,extract_goal,extract_personal_info
import pytz
from datetime import datetime, timedelta
from bson import ObjectId

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
        # print("\n\n COMMENT : ",comment)
        feedback_collection = get_feedback_collection()
        user_feedback = get_user_feedback(feedback_collection, user_id)
        handle_comment(user_feedback, response_id, comment)
        success, error = update_user_feedback(feedback_collection, user_id, user_feedback)
    
    elif feedback_type == "daily_reminders":
        # Directly refine the reminder from user_message and aira_response
        reminder = extract_reminder(user_message, aira_response)

        # Get the reminder collection
        reminder_collection = get_reminder_collection()

        # Set up Indian Standard Time (IST) timezone
        ist = pytz.timezone('Asia/Kolkata')
        
        # Get current time in UTC
        now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
        
        # Convert to Indian time for readability in logs
        now_ist = now_utc.astimezone(ist)
        print(f"Current time (IST): {now_ist}")

        # Determine the scheduled time based on user preference in IST
        reminder_time_preference = data.get("reminder_time", "morning")  # Default to morning
        
        # Create a base time in IST
        base_time_ist = now_ist.replace(microsecond=0)
        
        # Set the hours based on preference (in IST)
        if reminder_time_preference == "morning":
            base_time_ist = base_time_ist.replace(hour=8, minute=0, second=0)
        elif reminder_time_preference == "afternoon":
            base_time_ist = base_time_ist.replace(hour=14, minute=0, second=0)
        elif reminder_time_preference == "evening":
            base_time_ist = base_time_ist.replace(hour=19, minute=0, second=0)
        else:
            # Default to next morning at 8 AM IST
            tomorrow_ist = base_time_ist + timedelta(days=1)
            base_time_ist = tomorrow_ist.replace(hour=8, minute=0, second=0)

        # Ensure the scheduled time is in the future (in IST context)
        if base_time_ist < now_ist:
            base_time_ist = base_time_ist + timedelta(days=1)
        
        print(f"Scheduled time (IST): {base_time_ist}")
        
        # Convert back to UTC for storage
        scheduled_time_utc = base_time_ist.astimezone(pytz.UTC)
        # Format the time for storage
        formatted_time_ist = base_time_ist.strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"Scheduled time (UTC for storage): {formatted_time_ist}")

        # Check if a reminder already exists for this user and time slot
        existing_reminder = reminder_collection.find_one({
            "user_id": user_id,
            "reminders": {
                "$elemMatch": {
                    "scheduled_time": formatted_time_ist,
                    "status": "pending"
                }
            }
        })

        if existing_reminder:
            # A reminder already exists for this time slot
            success = True
            error = None
            print(f"Reminder already exists for {formatted_time_ist}, not adding a duplicate")
        else:
            # Prepare the reminder data with a unique _id
            reminder_data = {
                "_id": ObjectId(),
                "generated_reminder": reminder,
                "scheduled_time": formatted_time_ist,
                "status": "pending"
            }

            try:
                # Add the reminder to the user's document in the reminder collection
                reminder_collection.update_one(
                    {"user_id": user_id},
                    {"$push": {"reminders": reminder_data}},
                    upsert=True
                )
                success = True
                error = None
                print(f"Added new reminder for {formatted_time_ist}")
            except Exception as e:
                success = False
                error = (jsonify({"error": f"Failed to save reminder: {str(e)}"}), 500)
    
    elif feedback_type in ["goals", "personal_info"]:
        goals=extract_goal(user_message,aira_response)
        personal_info=extract_personal_info(user_message,aira_response)
        success, error = handle_personal_info_or_goals(
            user_id, response_id, goals, personal_info, feedback_type
        )
        #complete the code 
    
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
