from flask import Blueprint, request, jsonify
import time
import uuid
from utils import create_chain, store_chat_history 
from routes.auth import verify_jwt_token
from database.models import chat_history_collection
import logging
from bson import ObjectId
import re
from collections import Counter
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import nltk
from flask_cors import CORS
from database.models import get_collection
import random

logger = logging.getLogger(__name__)

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")
CORS(chat_bp, supports_credentials=True)

nltk.download("punkt")
nltk.download('punkt_tab')
nltk.download("stopwords")

brain_collection = get_collection("aira_brain")

def generate_ai_response(user_input: str, session_id: str,user_id) -> dict:
    """Generate AI response and store chat history."""
    start_time = time.time()
    print("\n\n\n\nuser id : ",user_id)
    ai_response = create_chain(user_id).invoke(
        {"input": user_input, "session_id": session_id},
        config={"configurable": {"session_id": session_id}}
    )
    response_time = round(time.time() - start_time, 2)
    response_id = str(uuid.uuid4())

    ai_message = {"role": "AI", "message": ai_response, "response_id": response_id, "created_at": time.time()}
    store_chat_history(session_id, user_input, ai_message)

    return {"response_id": response_id, "message": ai_response, "response_time": response_time}

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

@chat_bp.route("/new_session", methods=["POST"])
def new_session():
    """Create a new chat session for the user."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    session_id = str(ObjectId())
    session_data = {
        "session_id": session_id,
        "user_id": ObjectId(user_id),
        "title": "New Session",
        "messages": []
    }
    chat_history_collection.insert_one(session_data)

    print(f"Created new session: {session_id}")  # Debug
    return jsonify({"session_id": session_id, "session_title": "New Session"}), 201

@chat_bp.route("/start_intro", methods=["POST"])
def start_intro():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401

    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    # Check if intro session already exists
    session = chat_history_collection.find_one({"user_id": ObjectId(user_id), "title": "Introduction Session"})
    if session:
        return jsonify({
            "session_id": session["session_id"],
            "message": session["messages"][0]["content"]  # Return first message from AIRA
        }), 200

    # Create a new introduction session
    session_id = str(uuid.uuid4())
    first_message = "Hey there! 😊 I'm AIRA. I'd love to get to know you better. What's your name?"
    
    chat_history_collection.insert_one({
        "session_id": session_id,
        "user_id": ObjectId(user_id),
        "title": "Introduction Session",
        "messages": [
            {"role": "AI", "content": first_message, "created_at": time.time()}
        ],
        "created_at": time.time(),
    })

    return jsonify({
        "session_id": session_id,
        "message": first_message  # Return AIRA's first message
    }), 200



@chat_bp.route("/send", methods=["POST"])
def chat():
    """Handle sending a message and updating the session title based on AIRA's response."""

    # Authentication and input validation
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    user_input = data.get("message", "").strip()
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "Session ID required"}), 400

    # Define the fields and questions in order, starting with "name"
    brain_fields = ["name", "sex", "age", "height", "weight", "habits", "interests"]
    questions = [
        "Hey there! 😊 I'm AIRA. I'd love to get to know you better. What's your name?",  # Matches /start_intro
        "Great! How do you identify? (Male, Female, or Other)",
        "Awesome! How old are you?",
        "Got it! How tall are you? You can share in cm or feet.",
        "And what’s your weight? You can tell me in kg or lbs—whichever you prefer!",
        "Nice! Can you tell me about some of your daily habits?",
        "Lastly, what are some things you love doing? Any hobbies or interests?"
    ]


    # Find the session
    session = chat_history_collection.find_one({"session_id": session_id, "user_id": ObjectId(user_id)})
    if not session:
        return jsonify({"error": "Session not found or access denied"}), 403

    # Handle the Introduction Session
    if session["title"] == "Introduction Session":
        # Get current user data from the database
        user_data = brain_collection.find_one({"user_id": ObjectId(user_id)}) or {}
        current_field = session.get("current_field")

        # If current_field is not set, start with the first missing field
        if current_field is None:
            for field in brain_fields:
                if field not in user_data:
                    current_field = field
                    break
            else:
                current_field = None  # All fields are filled

        if current_field:
            question_index = brain_fields.index(current_field)
            question = questions[question_index]

            # If no user input yet, ask the current question
            if not user_input:
                ai_response = question
            else:
                # Extract only the current field's information
                extracted_value = extract_user_info(user_input, current_field)
                if extracted_value:
                    # Store the value in the brain_collection database
                    brain_collection.update_one(
                        {"user_id": ObjectId(user_id)},
                        {"$set": {current_field: extracted_value}},
                        upsert=True
                    )
                    # Update local user_data for the next check
                    user_data[current_field] = extracted_value
                    # Find the next missing field
                    next_field = None
                    for field in brain_fields[question_index + 1:]:
                        if field not in user_data:
                            next_field = field
                            break
                    if next_field:
                        ai_response = f"Got it! {questions[brain_fields.index(next_field)]}"
                        chat_history_collection.update_one(
                            {"session_id": session_id},
                            {"$set": {"current_field": next_field}}
                        )
                    else:
                        ai_response = "Thanks for sharing! 😊 Now we can have a more personalized conversation tailored just for you!"
                        chat_history_collection.update_one(
                            {"session_id": session_id},
                            {"$set": {"current_field": None}}
                        )
                else:
                    # If the response doesn’t match, ask the same question again
                    ai_response = f"I didn’t quite get that. {question}"

            # Update the chat history with messages
            messages = session.get("messages", [])
            if user_input:
                messages.append({"role": "User", "content": user_input, "created_at": time.time()})
            messages.append({"role": "AI", "content": ai_response, "created_at": time.time()})
            chat_history_collection.update_one(
                {"session_id": session_id},
                {"$set": {"messages": messages}}
            )
            return jsonify({"message": ai_response, "session_title": "Introduction Session"}), 200

        else:
            # Introduction complete, proceed to normal chat
            if user_input:
                response_data = generate_ai_response(user_input, session_id, user_id)
                return jsonify({**response_data, "session_title": "Introduction Session"}), 200
            return jsonify({"message": "Introduction complete. You can now start chatting.", "session_title": "Introduction Session"}), 200

    # Handle normal chat (non-introduction sessions)
    if not user_input:
        return jsonify({"error": "Message required for normal chat"}), 400
    
    response_data = generate_ai_response(user_input, session_id, user_id)

    # Ensure response_data is a dict and contains 'message'
    if isinstance(response_data, dict) and "message" in response_data:
        ai_response = response_data["message"].strip()
    else:
        ai_response = ""  # Fallback if key is missing

    print("ai_response:", ai_response)  # Debugging

    # Update title if it's the first message
    messages = session.get("messages", [])
    if len(messages) == 0 and ai_response:
        new_title = generate_title(ai_response)  # Use AIRA's response for title
        print("\n\n\nNew title:", new_title)  # Debugging
        chat_history_collection.update_one(
            {"session_id": session_id},
            {"$set": {"title": new_title}}
        )
        session_title = new_title
    else:
        session_title = session.get("title", "New Session")

    return jsonify({**response_data, "session_title": session_title}), 200


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

@chat_bp.route("/history", methods=["GET"])
def chat_history():
    """Fetch chat history for a specific session."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "Session ID required"}), 400

    try:
        session = chat_history_collection.find_one({"session_id": session_id, "user_id": ObjectId(user_id)})
        if not session:
            return jsonify({"error": "Session not found or access denied"}), 403
        return jsonify({"history": session.get("messages", []), "title": session.get("title", "New Session")}), 200
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        return jsonify({"error": "Internal server error"}), 500


@chat_bp.route("/sessions", methods=["GET"])
def get_sessions():
    """Retrieve user chat sessions."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    sessions = chat_history_collection.find({"user_id": ObjectId(user_id)})
    # Ensure sessions is in the correct format: list of dicts with session_id and session_title
    formatted_sessions = [
        {"session_id": session["session_id"], "session_title": session["title"]}
        for session in sessions
    ]
    return jsonify({"sessions": formatted_sessions}), 200