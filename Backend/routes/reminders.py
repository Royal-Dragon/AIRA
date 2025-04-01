from flask import Blueprint, request, jsonify
from routes.auth import verify_jwt_token
from database.models import reminder_collection, get_collection
import logging
from bson import ObjectId
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

reminder_bp = Blueprint("reminder", __name__, url_prefix="/api/reminder")

@reminder_bp.route("/get_due_reminders", methods=["GET"])
def get_due_reminders():
    """
    Retrieve all due reminders for a specific user.
    A reminder is due if its scheduled_time is <= current time (in UTC) and status is "pending".
    """
    user_id = request.args.get("user_id")
    current_time = datetime.utcnow()
    
    # Get timezone offset from request (optional)
    timezone_offset = request.args.get("timezone_offset", "0")  # in minutes from UTC
    try:
        offset_minutes = int(timezone_offset)
        # No need to adjust current_time - we keep everything in UTC for database operations
        print(f"\nUser timezone offset: {offset_minutes} minutes")
    except ValueError:
        offset_minutes = 0
    
    print(f"\nUSER ID: {user_id}")
    print(f"Current UTC time: {current_time}")
    
    # For India Standard Time (UTC+5:30), local time would be:
    india_time = current_time + timedelta(hours=5, minutes=30)
    print(f"Current time in India (IST): {india_time}")

    user = reminder_collection.find_one({"user_id": user_id})
    if not user:
        return jsonify({"reminders": []})

    # Get reminders that are due
    due_reminders = []
    for reminder in user.get("reminders", []):
        reminder_time = reminder["scheduled_time"]
        reminder_status = reminder["status"]
        is_due = reminder_time <= current_time
        
        print(f"\nReminder: {reminder['generated_reminder']}")
        print(f"Scheduled time (UTC): {reminder_time}")
        print(f"Scheduled time (IST): {reminder_time + timedelta(hours=5, minutes=30)}")
        print(f"Is due based on UTC? {is_due}, Status: {reminder_status}")
        
        if is_due and reminder_status == "pending":
            # Create a copy of the reminder for JSON serialization
            reminder_copy = reminder.copy()
            reminder_copy["_id"] = str(reminder_copy["_id"])
            reminder_copy["scheduled_time"] = reminder_copy["scheduled_time"].isoformat()
            due_reminders.append(reminder_copy)
    
    print(f"\nDue reminders: {due_reminders}")
    return jsonify({"reminders": due_reminders})

@reminder_bp.route("/update_reminder_status", methods=["POST"])
def update_reminder_status():
    data = request.json
    user_id = data["user_id"]
    reminder_id = data["reminder_id"]
    new_status = data["status"]  # "done" or "not_done"
    print("\nuser id : ",user_id)
    print("\reminder_id id : ",reminder_id)
    print("\new_status id : ",new_status)

    if new_status == "done":
        # Delete the reminder
        print("\n inside if")
        reminder_collection.update_one(
            {"user_id": user_id},
            {"$pull": {"reminders": {"_id": ObjectId(reminder_id)}}}
        )
        print("\n if done")
    elif new_status == "not_done":
        # Reschedule for 1 hour later
        new_time = datetime.utcnow() + timedelta(hours=1)

        reminder_collection.update_one(
            {"user_id": user_id, "reminders._id": ObjectId(reminder_id)},
            {"$set": {"reminders.$.scheduled_time": new_time, "reminders.$.status": "pending"}}
        )

    return jsonify({"message": "Reminder status updated"}), 200
