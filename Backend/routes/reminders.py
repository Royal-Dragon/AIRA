# from flask import Blueprint, request, jsonify
# from routes.auth import verify_jwt_token
# from database.models import reminder_collection, get_collection
# import logging
# from bson import ObjectId
# from datetime import datetime, timedelta
# import pytz

# logger = logging.getLogger(__name__)

# reminder_bp = Blueprint("reminder", __name__, url_prefix="/api/reminder")

# @reminder_bp.route("/get_due_reminders", methods=["GET"])
# def get_due_reminders():
#     """
#     Retrieve all due reminders for a specific user.
#     A reminder is due if its scheduled_time is <= current time and status is "pending".
#     Staggers multiple reminders by spacing them 10 minutes apart.
#     """
#     user_id = request.args.get("user_id")
    
#     # Get current time in UTC
#     current_time_utc = datetime.utcnow()
    
#     # For India Standard Time (UTC+5:30), local time would be:
#     india_time = current_time_utc + timedelta(hours=5, minutes=30)
#     print(f"Current time in UTC: {current_time_utc}")
#     print(f"Current time in India (IST): {india_time}")

#     user = reminder_collection.find_one({"user_id": user_id})
#     if not user:
#         return jsonify({"reminders": []})

#     # Get reminders that are due and sort them by scheduled_time
#     due_reminders = []
#     queued_reminders = []
    
#     for reminder in user.get("reminders", []):
#         # The scheduled_time field might be a datetime object or a string
#         reminder_time = reminder["scheduled_time"]
#         reminder_status = reminder["status"]
        
#         # Handle both string and datetime objects
#         if isinstance(reminder_time, str):
#             try:
#                 # Try to parse as ISO format first
#                 reminder_time = datetime.fromisoformat(reminder_time.replace('Z', '+00:00'))
#             except ValueError:
#                 try:
#                     # Try to parse as custom format
#                     reminder_time = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M:%S")
#                 except ValueError:
#                     # If all parsing fails, just log and skip
#                     print(f"Could not parse time: {reminder_time}")
#                     continue
        
#         # Check if reminder is due
#         is_due = reminder_time <= india_time
#         # print("\nreminder_time",reminder_time)
#         # print("\current_time_utc",india_time)
#         # print(f"\nReminder: {reminder['generated_reminder']}")
#         # print(f"Scheduled time (DB format): {reminder_time}")
#         # print(f"Is due? {is_due}, Status: {reminder_status}")
        
#         if is_due and reminder_status == "pending":
#             queued_reminders.append(reminder)
    
#     # Sort by scheduled time so we deliver oldest first
#     queued_reminders.sort(key=lambda r: r["scheduled_time"])
#     print("\n\nqueued_reminders",queued_reminders)
#     # Return only the first reminder that's due and reschedule the rest with 10-minute intervals
#     if queued_reminders:
#         # Take the first reminder to return immediately
#         first_reminder = queued_reminders[0]
#         first_reminder_copy = first_reminder.copy()
#         first_reminder_copy["_id"] = str(first_reminder_copy["_id"])
#         # Convert datetime to string for JSON serialization
#         if isinstance(first_reminder_copy["scheduled_time"], datetime):
#             first_reminder_copy["scheduled_time"] = first_reminder_copy["scheduled_time"].isoformat()
#         due_reminders.append(first_reminder_copy)
        
#         # Queue the rest with 10-minute intervals
#         next_delivery_time = current_time_utc + timedelta(minutes=10)
        
#         for i in range(1, len(queued_reminders)):
#             reminder = queued_reminders[i]
#             reminder_id = reminder["_id"]
            
#             # Update the scheduled time in the database
#             reminder_collection.update_one(
#                 {"user_id": user_id, "reminders._id": ObjectId(reminder_id)},
#                 {"$set": {"reminders.$.scheduled_time": next_delivery_time}}
#             )
            
#             next_delivery_time += timedelta(minutes=10)
#             print(f"Rescheduled reminder {i} to: {next_delivery_time}")
    
#     print(f"\nReturning due reminders: {due_reminders}")
#     return jsonify({"reminders": due_reminders})

# @reminder_bp.route("/update_reminder_status", methods=["POST"])
# def update_reminder_status():
#     data = request.json
#     user_id = data["user_id"]
#     reminder_id = data["reminder_id"]
#     new_status = data["status"]  # "done" or "not_done"
#     print("\nUser ID:", user_id)
#     print("Reminder ID:", reminder_id)
#     print("New Status:", new_status)

#     if new_status == "done":
#         # Delete the reminder
#         print("Processing 'done' status")
#         result = reminder_collection.update_one(
#             {"user_id": user_id},
#             {"$pull": {"reminders": {"_id": ObjectId(reminder_id)}}}
#         )
#         print(f"Deletion result: {result.modified_count} document(s) modified")
#     elif new_status == "not_done":
#         # Reschedule for 1 hour later
#         new_time = datetime.utcnow() + timedelta(hours=1)
        
#         result = reminder_collection.update_one(
#             {"user_id": user_id, "reminders._id": ObjectId(reminder_id)},
#             {"$set": {"reminders.$.scheduled_time": new_time, "reminders.$.status": "pending"}}
#         )
#         print(f"Rescheduled reminder to {new_time}. Result: {result.modified_count} document(s) modified")

#     return jsonify({"message": "Reminder status updated"}), 200