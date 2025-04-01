from database.models import get_collection
from bson.objectid import ObjectId
from datetime import datetime, timedelta
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

def get_brain_collection():
    """Retrieve the brain collection for storing personal info and goals."""
    return get_collection("aira_brain")

def validate_feedback_data(data):
    """Validate feedback submission data."""
    response_id = data.get("response_id")
    feedback_type = data.get("feedback_type")
    comment = data.get("comment", "").strip()
    
    # Updated valid feedback types
    valid_types = ["like", "dislike", "comment", "goals", "daily_reminders", "personal_info"]
    
    if not response_id or feedback_type not in valid_types:
        logger.warning(f"Invalid feedback data: response_id={response_id}, feedback_type={feedback_type}")
        return False, (jsonify({
            "error": "Invalid feedback data",
            "details": f"response_id and feedback_type {valid_types} are required."
        }), 400)
    
    if feedback_type == "comment" and not comment:
        return False, (jsonify({"error": "Comment required", "details": "Comment cannot be empty."}), 400)
    return True, None

def get_user_feedback(feedback_collection, user_id):
    """Fetch or initialize user feedback document."""
    user_feedback = feedback_collection.find_one({"_id": ObjectId(user_id)})
    if not user_feedback:
        user_feedback = {
            "_id": ObjectId(user_id), 
            "feedback": [], 
            "daily_reminders": []  # Updated from remembered_messages to daily_reminders
        }
    elif "remembered_messages" in user_feedback:
        # Migrate existing data structure if needed
        user_feedback["daily_reminders"] = user_feedback.pop("remembered_messages", [])
    
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
    """Retrieve user message and AI response for various feedback types."""
    chat_collection = get_collection("chat_history")
    chat_data = chat_collection.find_one({
        "user_id": ObjectId(user_id),
        "sessions.messages": {"$elemMatch": {"role": "AI", "response_id": {"$regex": response_id}}}
    })
    # print("\n chat_data : ",chat_data)
    if not chat_data:
        return None, None, (jsonify({"error": "Chat data not found"}), 404)
    
    user_message = None
    aira_response = None
    
    for session in chat_data.get("sessions", []):
        messages = session.get("messages", [])
        # print("\n Messages : ",messages)
        for i in range(len(messages)):
            msg = messages[i]
            # print("\n Messages : ",msg)
            if msg["role"] == "AI" and response_id in msg.get("response_id", ""):
                if i > 0 and messages[i - 1]["role"] == "User":
                    user_message = messages[i - 1]["content"]
                aira_response = msg["content"]
                break
        if aira_response:
            break
    print("\n\n aira response from feedback : ",aira_response)
    if not user_message or not aira_response:
        return None, None, (jsonify({"error": "Incomplete chat data"}), 400)
    
    return user_message, aira_response, None


def handle_daily_reminder(user_feedback, response_id, user_message, aira_response):
    """Handle 'daily_reminders' feedback by storing messages with expiration."""
    user_feedback["daily_reminders"].append({
        "response_id": response_id,
        "user_message": user_message,
        "aira_response": aira_response,
        "timestamp": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=1)  # Set expiration to 24 hours
    })
    
    # Clean up expired reminders
    current_time = datetime.utcnow()
    user_feedback["daily_reminders"] = [
        reminder for reminder in user_feedback["daily_reminders"] 
        if "expires_at" not in reminder or reminder["expires_at"] > current_time
    ]

def handle_personal_info_or_goals(user_id, response_id, user_message, aira_response, feedback_type):
    """Handle 'personal_info' or 'goals' feedback by storing in brain collection."""
    brain_collection = get_brain_collection()
    
    # Get or initialize user brain document
    print("\n\n BRAIN COLLECTION IN FEEDBACK",user_id)
    brain_doc = brain_collection.find_one({"user_id": ObjectId(user_id)})
    if not brain_doc:
        brain_doc = {
            "user_id": ObjectId(user_id),
            "name": "",
            "sex": "",
            "age": "",
            "height": "",
            "weight": "",
            "habits": "",
            "interests": "",
            "assessments": [],
            "personal_info": [],
            "goals": []
        }
    
    # Ensure the necessary lists exist
    if "personal_info" not in brain_doc:
        brain_doc["personal_info"] = []
    if "goals" not in brain_doc:
        brain_doc["goals"] = []
    
    # Add to the appropriate list
    entry = {
        "response_id": response_id,
        "user_message": user_message,
        "aira_response": aira_response,
        "timestamp": datetime.utcnow()
    }
    
    if feedback_type == "personal_info":
        brain_doc["personal_info"].append(entry)
    elif feedback_type == "goals":
        brain_doc["goals"].append(entry)
    
    # Update brain document
    try:
        brain_collection.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": brain_doc},
            upsert=True
        )
        return True, None
    except Exception as e:
        logger.error(f"Database error in handle_personal_info_or_goals: {str(e)}")
        return False, (jsonify({"error": "Database error", "details": str(e)}), 500)

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

def clean_expired_reminders():
    """Utility function to clean up expired reminders across all users."""
    try:
        feedback_collection = get_feedback_collection()
        current_time = datetime.utcnow()
        
        # Find all user documents
        users = feedback_collection.find({})
        
        for user in users:
            if "daily_reminders" in user:
                # Filter out expired reminders
                updated_reminders = [
                    reminder for reminder in user["daily_reminders"]
                    if "expires_at" not in reminder or reminder["expires_at"] > current_time
                ]
                
                # Update document if reminders were removed
                if len(updated_reminders) != len(user["daily_reminders"]):
                    feedback_collection.update_one(
                        {"_id": user["_id"]},
                        {"$set": {"daily_reminders": updated_reminders}}
                    )
        
        return True
    except Exception as e:
        logger.error(f"Error cleaning expired reminders: {str(e)}")
        return False
    
    