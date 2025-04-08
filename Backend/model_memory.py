import requests
from functools import lru_cache
from utils import GROQ_API_KEY
from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from operator import itemgetter


# Create a cached model factory to avoid recreating the model for each function call
@lru_cache(maxsize=1)
def get_model():
    """Returns a cached instance of the ChatGroq model"""
    return ChatGroq(groq_api_key=GROQ_API_KEY, model_name="Llama3-8b-8192")

def extract_from_conversation(user_message, aira_response, extraction_type):
    """Generic extraction function to avoid repetitive code"""
    model = get_model()
    
    # Define extraction configurations
    extraction_configs = {
        "reminder": {
            "task": "extract the main reminder or task from the conversation",
            "default": "No reminder detected."
        },
        "goal": {
            "task": "extract the main goal from the conversation",
            "default": "No goal detected."
        },
        "personal_info": {
            "task": "extract personal information from the conversation",
            "default": "No personal info detected."
        }
    }
    
    config = extraction_configs.get(extraction_type)
    if not config:
        return f"Invalid extraction type: {extraction_type}"
    
    system_prompt = f"""
    Your task is to {config['task']}.
    Return ONLY the {extraction_type} text in a simple format.
    If no {extraction_type} exists, return exactly "{config['default']}"
    """

    conversation = f"""
    User: {user_message}
    AI Assistant: {aira_response}
    
    What is the {extraction_type} in this conversation?
    Don't use this : 'The {extraction_type} in this conversation is:' just give the {extraction_type}.
    """

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=conversation)
    ]

    try:
        result = model.invoke(messages)
        
        if isinstance(result, AIMessage) and result.content.strip():
            return result.content.strip()
        else:
            return config['default']
    
    except Exception as e:
        print(f"Error processing {extraction_type}: {e}")
        return f"Error processing {extraction_type}."

# Simplified wrapper functions
def extract_reminder(user_message, aira_response):
    return extract_from_conversation(user_message, aira_response, "reminder")

def extract_goal(user_message, aira_response):
    return extract_from_conversation(user_message, aira_response, "goal")

def extract_personal_info(user_message, aira_response):
    return extract_from_conversation(user_message, aira_response, "personal_info")

def generate_user_story(user_data):
    """Generates a personalized user story based on available user data"""
    model = get_model()
    
    # Extract user data with proper fallbacks
    name = user_data.get("name", "This user")
    habits = user_data.get("habits", "None")
    interests = user_data.get("interests", "None")
    goals = [g["data"] for g in user_data.get("goals", [])] if user_data.get("goals") else []
    personal_info = [info["data"] for info in user_data.get("personal_info", [])] if user_data.get("personal_info") else []

    story_context = f"""
    You are AIRA, a thoughtful assistant. Write a short, inspiring 3-5 sentence story about the user's journey based on the data below.
    The tone should feel hopeful and motivating. This story will be shown in a welcome card on the user's dashboard.

    - Name: {name}
    - Habits: {habits}
    - Interests: {interests}
    - Goals: {', '.join(goals) if goals else 'None'}
    - Personal Info: {', '.join(personal_info) if personal_info else 'None'}

    Only output the short story. Do not include headings or explanations.
    """

    try:
        result = model.invoke(story_context)
        return result.content.strip() if hasattr(result, 'content') else str(result).strip()
    except Exception as e:
        print(f"Error generating user story: {e}")
        return f"Welcome, {name}! We're here to help you on your journey."

def generate_motivational_message_from_chat_history(chat_history):
    sessions = chat_history.get("sessions", [])

    # 1. Skip sessions titled "Introduction Session" or with empty messages
    valid_sessions = [
        s for s in sessions 
        if s.get("title") != "Introduction Session" and s.get("messages")
    ]

    if not valid_sessions:
        return "Wishing you a peaceful day ahead 🌼 – AIRA"

    # 2. Sort sessions by `last_active` descending (latest first)
    sorted_sessions = sorted(valid_sessions, key=itemgetter("last_active"), reverse=True)

    # 3. Collect messages from most recent sessions
    all_messages = []
    for session in sorted_sessions:
        all_messages.extend(session.get("messages", []))

    # 4. Filter out irrelevant/empty messages if needed
    filtered_messages = [m for m in all_messages if m.get("content")]

    # 5. Get the last 10 messages (User + AI)
    last_10_messages = filtered_messages[-10:]

    # 6. Format messages for prompt
    chat_text = "\n".join([
        f"{msg['role']}: {msg['content']}" 
        for msg in last_10_messages
    ])

    # 7. Generate motivational message with AIRA’s tone
    prompt = f"""
    You are AIRA, a friendly and supportive AI therapist. Based on the user’s recent messages, generate a **very short motivational message** (max 8 words) that reflects their passions, struggles, or energy.

    Guidelines:
    - Keep it extremely concise: **5–8 words only**
    - Make it feel personal and warm
    - Add 1 relevant emoji at most
    - Sound like AIRA: casual, kind, uplifting
    - Avoid generic phrases like “Have a nice day”

    Here are the recent messages:
    {chat_text}

    Now, generate a short motivational line:
    """

    model = get_model()
    result = model.invoke(prompt)

    return result.content.strip() if hasattr(result, 'content') else str(result).strip() or "Sending you strength and light today 🌟 – AIRA"

