import requests
from utils import GROQ_API_KEY
from langchain_groq import ChatGroq
from langchain.schema import SystemMessage, HumanMessage, AIMessage

def extract_reminder(user_message, aira_response):
    model = ChatGroq(groq_api_key=GROQ_API_KEY, model_name="Llama3-8b-8192")

    system_prompt = """
    Your task is to extract the main reminder or task from the conversation.
    Return ONLY the reminder text in a simple format.
    If no reminder exists, return exactly "No reminder detected."
    """

    conversation = f"""
    User: {user_message}
    AI Assistant: {aira_response}
    
    What is the reminder in this conversation?
    Don't use this : 'The reminder in this conversation is:' just give the reminder.
    """

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=conversation)
    ]

    try:
        result = model.invoke(messages)
        # print("🔍 Full API Response:", result)

        if isinstance(result, AIMessage) and result.content.strip():
            return result.content.strip()
        else:
            return "No reminder detected."
    
    except Exception as e:
        print(f"Error: {e}")
        return "Error processing reminder."

def extract_goal(user_message, aira_response):
    model = ChatGroq(groq_api_key=GROQ_API_KEY, model_name="Llama3-8b-8192")

    system_prompt = """
    Your task is to extract the main goal from the conversation.
    Return ONLY the goal text in a simple format.
    If no goal exists, return exactly "No goal detected."
    """

    conversation = f"""
    User: {user_message}
    AI Assistant: {aira_response}

    What is the goal in this conversation?
    Don't use this : 'The goal in this conversation is:' just give the goal.
    """

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=conversation)
    ]

    try:
        result = model.invoke(messages)
        # print("🔍 Full API Response:", result)

        if isinstance(result, AIMessage) and result.content.strip():
            return result.content.strip()
        else:
            return "No Goal detected."
    
    except Exception as e:
        print(f"Error: {e}")
        return "Error processing goal."
    
def extract_personal_info(user_message, aira_response):
    model = ChatGroq(groq_api_key=GROQ_API_KEY, model_name="Llama3-8b-8192")

    system_prompt = """
    Your task is to extract personal information from the conversation.
    Return ONLY the personal information in a simple format.
    If no personal information exists, return exactly "No personal info detected."
    """

    conversation = f"""
    User: {user_message}
    AI Assistant: {aira_response}
    
    What personal information is mentioned in this conversation?
    Don't use this : 'The personal information in this conversation is:' just give the information.
    """

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=conversation)
    ]

    try:
        result = model.invoke(messages)
        # print("🔍 Full API Response:", result)

        if isinstance(result, AIMessage) and result.content.strip():
            return result.content.strip()
        else:
            return "No personal info detected."
    
    except Exception as e:
        print(f"Error: {e}")
        return "Error processing personal info."
    
def generate_user_story(user_data):
    model = ChatGroq(groq_api_key=GROQ_API_KEY, model_name="Llama3-8b-8192")
    name = user_data.get("name", "This user")
    habits = user_data.get("habits", None)
    interests = user_data.get("interests", None)
    goals = [g["data"] for g in user_data.get("goals", [])]
    personal_info = [info["data"] for info in user_data.get("personal_info", [])]

    story_context = f"""
    You are AIRA, a thoughtful assistant. Write a short, inspiring 3-5 sentence story about the user's journey based on the data below.
    The tone should feel hopeful and motivating. This story will be shown in a welcome card on the user's dashboard.

    - Name: {name}
    - Habits: {habits or 'None'}
    - Interests: {interests or 'None'}
    - Goals: {', '.join(goals) if goals else 'None'}
    - Personal Info: {', '.join(personal_info) if personal_info else 'None'}

    Only output the short story. Do not include headings or explanations.
    """

    result = model.invoke(story_context)

    story_text = result.content.strip()
    return story_text