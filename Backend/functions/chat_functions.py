import time 
from essentials import find_similar_past_message
import uuid
from utils import create_chain, store_chat_history 
import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk
import logging
from database.models import chat_history_collection


nltk.download("punkt")
nltk.download('punkt_tab')
nltk.download("stopwords")

logger = logging.getLogger(__name__)

# Constants for auto-deletion
AUTO_DELETE_DAYS = 30  # Number of days after which to delete inactive sessions

def generate_ai_response(user_input: str, session_id: str, user_id, create_session=True) -> dict:
    """
    Generate AI response, check for past relevant messages, and store chat history.
    """
    start_time = time.time()
    print("\n\n\n\nuser id : ", user_id)

    # 🔹 Check AIRA's Brain for relevant past messages
    recalled_response = find_similar_past_message(user_id, user_input)

    if recalled_response:
        response_time = round(time.time() - start_time, 2)
        response_id = str(uuid.uuid4())

        ai_message = {
            "role": "AI",
            "message": recalled_response,  # Directly use refined response
            "response_id": response_id,
            "created_at": time.time()
        }

        # Only store in separate document if create_session is True
        if create_session:
            store_chat_history(session_id, user_input, ai_message)

        return {
            "role":"AI",
            "response_id": response_id,
            "message": ai_message["message"],
            "response_time": response_time
        }
    
    # 🔹 If no relevant past message, generate a fresh AI response
    ai_response = create_chain(user_id).invoke(
        {"input": user_input, "session_id": session_id},
        config={"configurable": {"session_id": session_id}}
    )

    response_time = round(time.time() - start_time, 2)
    response_id = str(uuid.uuid4())

    ai_message = {
        "role": "AI",
        "message": ai_response,
        "response_id": response_id,
        "created_at": time.time()
    }

    # Only store in separate document if create_session is True
    if create_session:
        store_chat_history(session_id, user_input, ai_message)

    return {
        "role":"AI",
        "response_id": response_id,
        "message": ai_response,
        "response_time": response_time
    }

def extract_name(user_input):
    # Common patterns like "I am Upendra", "My name is Upendra", "I'm Upendra"
    patterns = [
        r"\bmy name is ([A-Za-z]+)\b",
        r"\bi am ([A-Za-z]+)\b",
        r"\bi'm ([A-Za-z]+)\b",
        r"\bthis is ([A-Za-z]+)\b",
        r"\b([A-Za-z]+)\b"
    ]

    for pattern in patterns:
        match = re.search(pattern, user_input, re.IGNORECASE)
        if match:
            return match.group(1).capitalize()  # Extracted name
    
    return None  # No match found

def extract_user_info(user_input, field):
    """Extracts specific user information based on the expected field."""
    user_input = user_input.lower()

    if field == "name":
        return extract_name(user_input)  # Assuming you already have a function for extracting names

    elif field == "sex":
        if "male" in user_input:
            return "Male"
        elif "female" in user_input:
            return "Female"
        elif "other" in user_input:
            return "Other"

    elif field == "age":
        match = re.search(r"(\d{1,2})\s*(years? old|y/o|yr|yrs|age)?", user_input)
        return match.group(1) if match else None

    elif field == "height":
        match_cm = re.search(r"(\d{2,3})\s*(cm|centimeters?)", user_input)
        match_ft = re.search(r"(\d)'(\d{1,2})", user_input)  # Example: 5'11
        if match_cm:
            return f"{match_cm.group(1)} cm"
        elif match_ft:
            return f"{match_ft.group(1)}' {match_ft.group(2)}"

    elif field == "weight":
        match_kg = re.search(r"(\d{2,3})\s*(kg|kilograms?)", user_input)
        match_lbs = re.search(r"(\d{2,3})\s*(lbs|pounds?)", user_input)
        if match_kg:
            return f"{match_kg.group(1)} kg"
        elif match_lbs:
            return f"{match_lbs.group(1)} lbs"

    elif field == "habits":
        return user_input  # Can improve with NLP, but for now, store directly

    elif field == "interests":
        return user_input  # Store hobbies/interests as-is

    return None  # If nothing extracted

def extract_keywords(text):
    """Extracts meaningful words from text while filtering stopwords."""
    stop_words = set(stopwords.words("english"))
    words = word_tokenize(text)
    filtered_words = [word for word in words if word.lower() not in stop_words and word.isalnum()]
    return filtered_words

# Define words to avoid in titles
negative_words = {"stressful", "tired", "worried", "anxious", "nervous", "sad", "bad", "boring", "exams", "breakup"}

def generate_title(aira_response):
    """Generates a short, natural title (4-5 words) based on AIRA's response."""

    # Tokenize response into sentences and words
    words = word_tokenize(aira_response)

    # Remove stopwords and non-alphabetic words
    stop_words = set(stopwords.words("english"))
    meaningful_words = [word for word in words if word.lower() not in stop_words and word.isalnum()]
    print("meaning ful words : ",meaningful_words)
    # Pick the first 4-5 meaningful words
    title_words = meaningful_words[:5]  # Keep only the first few important words
    
    # Create a natural title
    title = " ".join(title_words).title() if title_words else "New Chat"

    return title

# Setup a scheduled task for auto-deletion
def setup_auto_deletion_task():
    """
    Sets up a scheduled task to delete old sessions.
    This function should be called when the application starts.
    """
    import threading
    import schedule
    import time
    
    def run_cleanup():
        logger.info("Running automated session cleanup")
        cutoff_time = time.time() - (AUTO_DELETE_DAYS * 24 * 60 * 60)
        
        # Find all user documents
        user_docs = chat_history_collection.find({})
        for user_doc in user_docs:
            if "sessions" not in user_doc:
                continue
                
            user_id = user_doc["user_id"]
            active_sessions = []
            for session in user_doc["sessions"]:
                if session["title"] == "Introduction Session" or session["last_active"] >= cutoff_time:
                    active_sessions.append(session)
            
            deleted_count = len(user_doc["sessions"]) - len(active_sessions)
            
            if deleted_count > 0:
                chat_history_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"sessions": active_sessions}}
                )
                logger.info(f"Auto-cleaned {deleted_count} old sessions for user: {user_id}")
    
    def run_scheduler():
        schedule.every().day.at("03:00").do(run_cleanup)  # Run at 3 AM every day
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True  # Allow the thread to exit when the main program exits
    scheduler_thread.start()
    logger.info("Auto-deletion scheduler started")