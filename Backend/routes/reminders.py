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

@reminder_bp.route("/get_due_reminders", methods=["GET"])
def get_due_reminders():
    """
    Retrieve all due reminders for a specific user.
    A reminder is due if its scheduled_time is <= current time and status is "pending".
    Staggers multiple reminders by spacing them 10 minutes apart.
    """
    user_id = request.args.get("user_id")
    
    # Get current time in UTC and IST
    current_time_utc = datetime.now(utc_tz)
    current_time_ist = current_time_utc.astimezone(ist_tz)
    
    logger.info(f"Current time in UTC: {current_time_utc}")
    logger.info(f"Current time in India (IST): {current_time_ist}")

    user = reminder_collection.find_one({"user_id": user_id})
    if not user:
        return jsonify({"reminders": []})

    # Get reminders that are due and sort them by scheduled_time
    due_reminders = []
    queued_reminders = []
    
    for reminder in user.get("reminders", []):
        # Parse the reminder time and ensure it has timezone info
        reminder_time = reminder["scheduled_time"]
        reminder_status = reminder["status"]
        
        # Convert to datetime object with timezone if it's not already
        if isinstance(reminder_time, str):
            try:
                # Try to parse as ISO format first
                parsed_time = datetime.fromisoformat(reminder_time.replace('Z', '+00:00'))
                
                # If no timezone info, assume it's in IST
                if parsed_time.tzinfo is None:
                    reminder_time = ist_tz.localize(parsed_time)
                else:
                    reminder_time = parsed_time
            except ValueError:
                try:
                    # Try to parse as custom format
                    parsed_time = datetime.strptime(reminder_time, "%Y-%m-%d %H:%M:%S")
                    
                    # Assume the time is in IST
                    reminder_time = ist_tz.localize(parsed_time)
                except ValueError:
                    # If all parsing fails, just log and skip
                    logger.error(f"Could not parse time: {reminder_time}")
                    continue
        elif isinstance(reminder_time, datetime) and reminder_time.tzinfo is None:
            # If it's a naive datetime, assume it's in IST
            reminder_time = ist_tz.localize(reminder_time)
        
        # Check if reminder is due (compare in IST)
        is_due = reminder_time <= current_time_ist
        
        if is_due and reminder_status == "pending":
            queued_reminders.append({
                **reminder,
                "scheduled_time": reminder_time  # Store the datetime object with timezone
            })
    
    # Sort by scheduled time so we deliver oldest first
    queued_reminders.sort(key=lambda r: r["scheduled_time"])
    logger.info(f"Queued reminders: {queued_reminders}")
    
    # Return only the first reminder that's due and reschedule the rest with 10-minute intervals
    if queued_reminders:
        # Take the first reminder to return immediately
        first_reminder = queued_reminders[0]
        first_reminder_copy = first_reminder.copy()
        first_reminder_copy["_id"] = str(first_reminder_copy["_id"])
        
        # Format datetime as string without timezone info for JSON serialization
        first_reminder_copy["scheduled_time"] = format_datetime_for_response(first_reminder_copy["scheduled_time"])
        due_reminders.append(first_reminder_copy)
        
        # Queue the rest with 10-minute intervals
        next_delivery_time = current_time_ist + timedelta(minutes=10)
        
        for i in range(1, len(queued_reminders)):
            reminder = queued_reminders[i]
            reminder_id = reminder["_id"]
            
            # Convert next_delivery_time to UTC for storage
            next_delivery_time_utc = next_delivery_time.astimezone(utc_tz)
            
            # Update the scheduled time in the database
            reminder_collection.update_one(
                {"user_id": user_id, "reminders._id": ObjectId(reminder_id)},
                {"$set": {"reminders.$.scheduled_time": next_delivery_time_utc}}
            )
            
            next_delivery_time += timedelta(minutes=10)
            logger.info(f"Rescheduled reminder {i} to: {next_delivery_time} IST")
    
    logger.info(f"Returning due reminders: {due_reminders}")
    return jsonify({"reminders": due_reminders})

@reminder_bp.route("/update_reminder_status", methods=["POST"])
def update_reminder_status():
    try:
        data = request.json
        user_id = data.get("user_id")
        reminder_id = data.get("reminder_id")
        new_status = data.get("status")  # "done" or "not_done"

        if not user_id or not reminder_id or not new_status:
            return jsonify({"error": "Missing required fields"}), 400

        logger.info(f"User ID: {user_id}")
        logger.info(f"Reminder ID: {reminder_id}")
        logger.info(f"New Status: {new_status}")

        if new_status == "done":
            # Delete the reminder
            logger.info("Processing 'done' status")
            result = reminder_collection.update_one(
                {"user_id": user_id},
                {"$pull": {"reminders": {"_id": ObjectId(reminder_id)}}}
            )
            logger.info(f"Deletion result: {result.modified_count} document(s) modified")
        elif new_status == "not_done":
            # Get the current time in IST, then add 1 hour
            current_time_ist = datetime.now(ist_tz)
            new_time_ist = current_time_ist + timedelta(hours=1)
            
            # Format for storage in a consistent format (without timezone info)
            formatted_time = new_time_ist.strftime("%Y-%m-%d %H:%M:%S")
            
            # Update in database 
            result = reminder_collection.update_one(
                {"user_id": user_id, "reminders._id": ObjectId(reminder_id)},
                {"$set": {"reminders.$.scheduled_time": formatted_time, "reminders.$.status": "pending"}}
            )
            logger.info(f"Rescheduled reminder to {formatted_time}. Result: {result.modified_count} document(s) modified")
        else:
            return jsonify({"error": "Invalid status"}), 400
        
        return jsonify({"message": "Reminder status updated"}), 200
    except Exception as e:
        logger.error(f"Error updating reminder status: {str(e)}")
        return jsonify({"error": "An error occurred while updating the reminder"}), 500
    
@reminder_bp.route("/add_reminder", methods=["POST"])
def add_reminder():
    """
    Add a new reminder for a user
    Expects JSON body with: user_id, title, scheduled_time (in IST)
    Stores scheduled_time in IST directly
    """
    try:
        data = request.json
        user_id = data.get("user_id")
        title = data.get("title")
        scheduled_time = data.get("scheduled_time")  # Expected in IST format: "YYYY-MM-DD HH:MM:SS"

        if not all([user_id, title, scheduled_time]):
            return jsonify({"error": "Missing required fields (user_id, title, scheduled_time)"}), 400

        # Parse the incoming IST time WITHOUT localizing it first
        try:
            # Parse as naive datetime
            naive_datetime = datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M:%S")
            # Explicitly set as IST
            ist_datetime = ist_tz.localize(naive_datetime)
            # Store the UTC equivalent for MongoDB (which stores in UTC)
            utc_datetime = ist_datetime.astimezone(pytz.UTC)
        except ValueError as e:
            logger.error(f"Invalid scheduled_time format: {str(e)}")
            return jsonify({"error": "Invalid scheduled_time format. Use YYYY-MM-DD HH:MM:SS"}), 400

        # Create new reminder object, storing scheduled_time in UTC for MongoDB
        new_reminder = {
            "_id": ObjectId(),
            "title": title,
            "scheduled_time": utc_datetime,  # Store in UTC for MongoDB
            "time_zone": "Asia/Kolkata",  # Store the time zone reference
            "status": "pending",
            "created_at": datetime.now(pytz.UTC)  # Store creation time in UTC
        }

        # Add reminder to user's reminders array
        result = reminder_collection.update_one(
            {"user_id": user_id},
            {"$push": {"reminders": new_reminder}},
            upsert=True  # Creates new document if user doesn't exist
        )

        if result.modified_count > 0 or result.upserted_id:
            # Convert back to IST string for response (remove timezone info)
            new_reminder_copy = new_reminder.copy()
            new_reminder_copy["_id"] = str(new_reminder_copy["_id"])
            # Convert UTC time back to IST for response
            ist_time = new_reminder_copy["scheduled_time"].astimezone(ist_tz)
            new_reminder_copy["scheduled_time"] = format_datetime_for_response(ist_time)
            ist_created_at = new_reminder_copy["created_at"].astimezone(ist_tz)
            new_reminder_copy["created_at"] = format_datetime_for_response(ist_created_at)
            
            return jsonify({
                "message": "Reminder added successfully",
                "reminder": new_reminder_copy
            }), 201
        else:
            return jsonify({"error": "Failed to add reminder"}), 500

    except Exception as e:
        logger.error(f"Error adding reminder: {str(e)}")
        return jsonify({"error": "An error occurred while adding the reminder"}), 500

@reminder_bp.route("/update_reminder", methods=["PUT"])
def update_reminder():
    """
    Update an existing reminder
    Expects JSON body with: user_id, reminder_id, title (optional), scheduled_time (optional, in IST)
    Stores scheduled_time in UTC for MongoDB with time zone reference
    """
    try:
        data = request.json
        user_id = data.get("user_id")
        reminder_id = data.get("reminder_id")
        title = data.get("title")
        scheduled_time = data.get("scheduled_time")  # Expected in IST format: "YYYY-MM-DD HH:MM:SS"

        if not user_id or not reminder_id:
            return jsonify({"error": "Missing required fields (user_id, reminder_id)"}), 400

        # Prepare update fields
        update_fields = {}
        if title:
            update_fields["reminders.$.title"] = title
        if scheduled_time:
            try:
                # Parse naive datetime, explicitly set as IST, then convert to UTC
                naive_datetime = datetime.strptime(scheduled_time, "%Y-%m-%d %H:%M:%S")
                ist_datetime = ist_tz.localize(naive_datetime)
                utc_datetime = ist_datetime.astimezone(pytz.UTC)
                update_fields["reminders.$.scheduled_time"] = utc_datetime  # Store in UTC
                update_fields["reminders.$.time_zone"] = "Asia/Kolkata"  # Store time zone reference
            except ValueError as e:
                logger.error(f"Invalid scheduled_time format: {str(e)}")
                return jsonify({"error": "Invalid scheduled_time format. Use YYYY-MM-DD HH:MM:SS"}), 400

        if not update_fields:
            return jsonify({"error": "No fields to update"}), 400

        # Update the reminder
        result = reminder_collection.update_one(
            {"user_id": user_id, "reminders._id": ObjectId(reminder_id)},
            {"$set": update_fields}
        )

        if result.modified_count > 0:
            return jsonify({"message": "Reminder updated successfully"}), 200
        else:
            return jsonify({"error": "Reminder not found or no changes made"}), 404

    except Exception as e:
        logger.error(f"Error updating reminder: {str(e)}")
        return jsonify({"error": "An error occurred while updating the reminder"}), 500

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

# Make sure to add this import at the top of your file
import pytz
# Define IST timezone
ist_tz = pytz.timezone('Asia/Kolkata')