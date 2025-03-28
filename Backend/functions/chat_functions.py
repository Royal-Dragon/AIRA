import time 
from essentials import find_similar_past_message
import uuid
from utils import create_chain, store_chat_history 
import re
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk


nltk.download("punkt")
nltk.download('punkt_tab')
nltk.download("stopwords")


def generate_ai_response(user_input: str, session_id: str, user_id) -> dict:
    """Generate AI response, check for past relevant messages, and store chat history."""
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

        store_chat_history(session_id, user_input, ai_message)

        return {
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

    store_chat_history(session_id, user_input, ai_message)

    return {
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
        r"\bthis is ([A-Za-z]+)\b"
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