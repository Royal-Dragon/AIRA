from bson import ObjectId
from database.models import get_collection
from datetime import datetime
from model_memory import extract_reminder

def get_user_reminders(user_id):
    # Ensure user_id is an ObjectId
    try:
        if not isinstance(user_id, ObjectId):
            user_id_obj = ObjectId(user_id)
        else:
            user_id_obj = user_id
    except:
        print(f"Invalid user_id format: {user_id}")
        return "User"  # Default if ID format is invalid
    
    # Query the database
    try:
        feedback_collection = get_collection("feedback")
        feedback_data = feedback_collection.find_one({"_id": user_id_obj})
        # print("\n\n feedback data : ",feedback_data)
        # Check if user_data exists and has a name field
        if feedback_data:
            return feedback_data
        else:
            print(f"No name found for user_id: {user_id}")
            return "User"  # Default if name not found
    except Exception as e:
        print(f"Error retrieving user name: {str(e)}")
        return "User"  # Default in case of any error


def get_valid_reminders(feedback_data):
    now = datetime.utcnow()  # Ensure you're using UTC to match MongoDB timestamps
    reminders = feedback_data.get("daily_reminders", [])

    # Filter out expired reminders
    valid_reminders = [
        reminder for reminder in reminders if reminder["expires_at"] > now
    ]

    return valid_reminders

def format_reminders_message(reminders):
    if not reminders:
        return "You don't have any active reminders for today.", None, None

    print("\n\n REMINDERS : ", reminders)

    # Create formatted string for display
    reminder_text = "\n".join(
        [
            f"{i+1}. {reminder['user_message']}"  # Use 'user_message' instead of 'reminder_text'
            for i, reminder in enumerate(reminders)
        ]
    )
    formatted_message = f"Here are your reminders for today:\n{reminder_text}"
    
    # Extract user messages and AIRA responses as separate lists
    user_messages = [reminder['user_message'] for reminder in reminders]
    aira_responses = [reminder['aira_response'] for reminder in reminders]
    
    return formatted_message, user_messages, aira_responses

