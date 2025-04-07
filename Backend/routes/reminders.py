from flask import Blueprint, request, jsonify
from routes.auth import verify_jwt_token
from database.models import reminder_collection, get_collection
import logging
from bson import ObjectId
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)

reminder_bp = Blueprint("reminder", __name__, url_prefix="/api/reminder")

# Define timezone objects
utc_tz = pytz.UTC
ist_tz = pytz.timezone('Asia/Kolkata')  # India Standard Time

def convert_to_ist(utc_time):
    """Convert UTC datetime to IST datetime"""
    if isinstance(utc_time, str):
        try:
            utc_time = datetime.fromisoformat(utc_time.replace('Z', '+00:00'))
        except ValueError:
            try:
                utc_time = datetime.strptime(utc_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logger.error(f"Could not parse time: {utc_time}")
                return None
    
    # Ensure UTC time has timezone info
    if utc_time.tzinfo is None:
        utc_time = utc_tz.localize(utc_time)
        
    # Convert to IST
    return utc_time.astimezone(ist_tz)

def convert_to_utc(ist_time):
    """Convert IST datetime to UTC datetime"""
    if isinstance(ist_time, str):
        try:
            # Try to parse the string as a datetime
            naive_time = datetime.fromisoformat(ist_time.replace('Z', '+00:00'))
            if naive_time.tzinfo is None:
                # If no timezone info, assume it's IST
                ist_time = ist_tz.localize(naive_time)
            else:
                ist_time = naive_time
        except ValueError:
            try:
                naive_time = datetime.strptime(ist_time, "%Y-%m-%d %H:%M:%S")
                ist_time = ist_tz.localize(naive_time)
            except ValueError:
                logger.error(f"Could not parse time: {ist_time}")
                return None
    elif isinstance(ist_time, datetime) and ist_time.tzinfo is None:
        # If datetime but no timezone, assume it's IST
        ist_time = ist_tz.localize(ist_time)
    
    # Convert to UTC
    return ist_time.astimezone(utc_tz)

def format_datetime_for_response(dt):
    """Format datetime object to a consistent string format without timezone info"""
    if isinstance(dt, datetime):
        # Convert to IST if it has timezone info
        if dt.tzinfo is not None:
            dt = dt.astimezone(ist_tz)
        # Return format: "YYYY-MM-DD HH:MM:SS"
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    return dt

@reminder_bp.route("/get_all_reminders", methods=["GET"])
def get_all_reminders():
    """
    Retrieve all reminders for a specific user regardless of due status.
    Returns reminders sorted by scheduled_time (earliest first).
    Handles dates stored as strings in IST format.
    """
    user_id = request.args.get("user_id")
    
    # Get current time in IST for comparison
    current_time = datetime.now()
    current_time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    logger.info(f"Current time in IST: {current_time_str}")

    # Find the user document
    user = reminder_collection.find_one({"user_id": user_id})
    if not user:
        return jsonify({"reminders": []})

    # Process all reminders
    all_reminders = []
    
    for reminder in user.get("reminders", []):
        # Create a copy of the reminder for response
        reminder_copy = reminder.copy()
        reminder_copy["_id"] = str(reminder_copy["_id"])
        
        # Get the scheduled time as string
        scheduled_time_str = reminder["scheduled_time"]
        
        # Add a field to indicate if the reminder is due
        # Compare string dates directly or parse if necessary
        try:
            is_due = False
            if isinstance(scheduled_time_str, str):
                # Parse strings to datetime objects for comparison
                scheduled_datetime = datetime.strptime(scheduled_time_str, "%Y-%m-%d %H:%M:%S")
                is_due = scheduled_datetime <= current_time and reminder["status"] == "pending"
            else:
                # Handle any non-string scheduled_time (fallback)
                logger.warning(f"Unexpected scheduled_time format: {type(scheduled_time_str)}")
                scheduled_time_str = str(scheduled_time_str)
        except ValueError as e:
            logger.error(f"Error parsing scheduled_time: {e}")
            is_due = False
            
        reminder_copy["is_due"] = is_due
        all_reminders.append(reminder_copy)
    
    # Sort by scheduled time (earliest first)
    all_reminders.sort(key=lambda r: r["scheduled_time"])
    
    logger.info(f"Returning all reminders: {len(all_reminders)} found")
    return jsonify({"reminders": all_reminders})

@reminder_bp.route("/update_reminder", methods=["POST"])
def update_reminder():
    try:
        # Parse request data
        data = request.json
        user_id = data.get("user_id")
        reminder_id = data.get("reminder_id")
        generated_reminder = data.get("title")  # Request uses "title", mapped to "generated_reminder"
        scheduled_time = data.get("scheduled_time")
        status = data.get("status")

        # Validate required fields
        if not user_id or not reminder_id:
            return jsonify({"error": "Missing required fields (user_id, reminder_id)"}), 400

        # Case 1: Status is provided
        if status:
            if status == "done":
                # Delete the reminder
                logger.info("Processing 'done' status")
                result = reminder_collection.update_one(
                    {"user_id": user_id},
                    {"$pull": {"reminders": {"_id": ObjectId(reminder_id)}}}
                )
                if result.modified_count > 0:
                    logger.info(f"Deletion result: {result.modified_count} document(s) modified")
                    return jsonify({"message": "Reminder deleted successfully"}), 200
                else:
                    return jsonify({"error": "Reminder not found"}), 404

            elif status == "not_done":  # Handle both formats
                # Parse the scheduled time string to datetime
                try:
                    current_time = datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M:%S")
                    # Add 1 hour
                    new_time = current_time + timedelta(hours=1)
                    # Format back to string
                    formatted_time = new_time.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError as e:
                    logger.error(f"Invalid scheduled_time format: {str(e)}")
                    return jsonify({"error": "Invalid scheduled_time format. Use YYYY-MM-DD HH:MM:SS"}), 400

                # Prepare update fields
                update_fields = {
                    "reminders.$.scheduled_time": formatted_time,
                    "reminders.$.status": "pending"
                }
                if generated_reminder:
                    update_fields["reminders.$.generated_reminder"] = generated_reminder

                # Update the reminder
                result = reminder_collection.update_one(
                    {"user_id": user_id, "reminders._id": ObjectId(reminder_id)},
                    {"$set": update_fields}
                )
                if result.modified_count > 0:
                    logger.info(f"Rescheduled reminder to {formatted_time}. Updated fields: {update_fields}")
                    return jsonify({
                        "message": "Reminder rescheduled and updated successfully",
                        "new_scheduled_time": formatted_time
                    }), 200
                else:
                    return jsonify({"error": "Reminder not found"}), 404

            else:
                return jsonify({"error": "Invalid status"}), 400

        # Case 2: No status provided, update fields as provided
        else:
            update_fields = {}
            if generated_reminder:
                update_fields["reminders.$.generated_reminder"] = generated_reminder
            if scheduled_time:
                try:
                    # Validate scheduled_time format
                    datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M:%S")
                    update_fields["reminders.$.scheduled_time"] = scheduled_time
                except ValueError:
                    return jsonify({"error": "Invalid scheduled_time format. Use YYYY-MM-DD HH:MM:%S"}), 400

            # If no fields to update, return an error
            if not update_fields:
                return jsonify({"error": "No fields to update"}), 400

            # Perform the update
            result = reminder_collection.update_one(
                {"user_id": user_id, "reminders._id": ObjectId(reminder_id)},
                {"$set": update_fields}
            )
            if result.modified_count > 0:
                logger.info(f"Updated reminder with fields: {update_fields}")
                return jsonify({"message": "Reminder updated successfully"}), 200
            else:
                return jsonify({"error": "Reminder not found or no changes made"}), 404

    except Exception as e:
        logger.error(f"Error updating reminder: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
    
@reminder_bp.route("/add_reminder", methods=["POST"])
def add_reminder():
    """
    Add a new reminder for a user.
    Expects JSON body with: user_id, title, scheduled_time (in IST).
    Stores scheduled_time and created_at as strings in IST format ("YYYY-MM-DD HH:MM:SS").
    Returns them in the same IST format.
    """
    try:
        data = request.json
        user_id = data.get("user_id")
        title = data.get("title")
        scheduled_time = data.get("scheduled_time")  # Expected in IST format: "YYYY-MM-DD HH:MM:SS"

        # Validate required fields
        if not all([user_id, title, scheduled_time]):
            return jsonify({"error": "Missing required fields (user_id, title, scheduled_time)"}), 400

        # Parse the incoming scheduled_time (assumed to be IST)
        try:
            # Parse as naive datetime
            naive_datetime = datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M:%S")
            # Localize to IST to confirm it’s treated as IST
            ist_datetime = ist_tz.localize(naive_datetime)
        except ValueError as e:
            logger.error(f"Invalid scheduled_time format: {str(e)}")
            return jsonify({"error": "Invalid scheduled_time format. Use YYYY-MM-DD HH:MM:SS"}), 400

        # Get current time in IST
        ist_datetime_now = datetime.now(ist_tz)

        # Format times as IST strings for storage
        scheduled_time_ist_str = ist_datetime.strftime("%Y-%m-%d %H:%M:%S")
        created_at_ist_str = ist_datetime_now.strftime("%Y-%m-%d %H:%M:%S")

        # Create new reminder object, storing times as IST strings
        new_reminder = {
            "_id": ObjectId(),
            "generated_reminder": title,
            "scheduled_time": scheduled_time_ist_str,  # Store as IST string
            "status": "pending",
            "created_at": created_at_ist_str,  # Store as IST string
        }

        # Add reminder to user's reminders array in MongoDB
        result = reminder_collection.update_one(
            {"user_id": user_id},
            {"$push": {"reminders": new_reminder}},
            upsert=True  # Creates new document if user doesn’t exist
        )

        # Check if the operation was successful
        if result.modified_count > 0 or result.upserted_id:
            # Prepare response: times are already IST strings
            new_reminder_copy = new_reminder.copy()
            new_reminder_copy["_id"] = str(new_reminder_copy["_id"])  # Convert ObjectId to string
            return jsonify({
                "message": "Reminder added successfully",
                "reminder": new_reminder_copy
            }), 201
        else:
            return jsonify({"error": "Failed to add reminder"}), 500

    except Exception as e:
        logger.error(f"Error adding reminder: {str(e)}")
        return jsonify({"error": "An error occurred while adding the reminder"}), 500


@reminder_bp.route("/delete_reminder", methods=["DELETE"])
def delete_reminder():
    """
    Delete a specific reminder
    Expects JSON body with: user_id, reminder_id
    """
    try:
        data = request.json
        user_id = data.get("user_id")
        reminder_id = data.get("reminder_id")

        if not user_id or not reminder_id:
            return jsonify({"error": "Missing required fields (user_id, reminder_id)"}), 400

        # Delete the reminder from the array
        result = reminder_collection.update_one(
            {"user_id": user_id},
            {"$pull": {"reminders": {"_id": ObjectId(reminder_id)}}}
        )

        if result.modified_count > 0:
            return jsonify({"message": "Reminder deleted successfully"}), 200
        else:
            return jsonify({"error": "Reminder not found"}), 404

    except Exception as e:
        logger.error(f"Error deleting reminder: {str(e)}")
        return jsonify({"error": "An error occurred while deleting the reminder"}), 500
