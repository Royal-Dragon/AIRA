from database.models import brain_collection
from bson import ObjectId

CATEGORY_KEYWORDS = {
    "goals": [
        "goal", "achieve", "plan", "long-term", "future",  # Original
        "objective", "success", "milestone", "dream", "aspire",  # Added
        "progress", "target", "ambition", "strategy", "priority"
    ],
    "reminders": [
        "remind", "today", "schedule", "appointment", "meeting",  # Original
        "task", "deadline", "event", "due", "alert",  # Added
        "calendar", "notify", "tomorrow", "upcoming", "time"
    ],
    "personal_details": [
        "family", "friend", "love", "stress", "happy", "sad",  # Original
        "relationship", "emotion", "feeling", "anxiety", "joy",  # Added
        "partner", "mood", "support", "worry", "life"
    ],
    "casual_chat": [
        # Original (empty)
        "hey", "chat", "talk", "weather", "day",  # Added
        "cool", "fun", "random", "nice", "how’s it going"
    ]
}

def get_user_details(user_id):
    """Fetch user details from Brain collection."""
    user_data = brain_collection.find_one(
        {"user_id": ObjectId(user_id)},
        {"_id": 0, "name": 1, "age": 1, "sex": 1, "height": 1, "weight": 1, "interests": 1, "hobbies": 1}
    )

    return user_data if user_data else {}