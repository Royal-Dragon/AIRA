import pytz
from datetime import datetime, timedelta
from textblob import TextBlob  # For sentiment analysis
from pymongo import MongoClient
from database.models import chat_history_collection

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["your_database"]
mental_status_collection = db["mental_status"]

def analyze_sentiment(text):
    """
    Perform sentiment analysis on the given text.
    Returns a sentiment score between -1 (negative) to 1 (positive).
    """
    analysis = TextBlob(text)
    return analysis.sentiment.polarity  # Ranges from -1 to 1

def get_user_sentiment(user_id, date_str):
    """
    Retrieves all user messages for a given date and calculates the average sentiment score.
    """
    start_time = f"{date_str} 00:00:00"
    end_time = f"{date_str} 23:59:59"

    # Convert to datetime objects
    start_time_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
    end_time_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")

    # Retrieve all sessions for the user
    user_sessions = chat_history_collection.find({"messages.role": "User", "messages.created_at": {"$gte": start_time, "$lte": end_time}})
    
    sentiment_scores = []
    
    for session in user_sessions:
        for message in session["messages"]:
            if message["role"] == "User" and start_time <= message["created_at"] <= end_time:
                sentiment_scores.append(analyze_sentiment(message["content"]))

    # Calculate the average sentiment score
    avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0

    # Store the daily sentiment score in the database
    mental_status_collection.update_one(
        {"user_id": user_id, "date": date_str},
        {"$set": {"sentiment_score": avg_sentiment}},
        upsert=True
    )

    return avg_sentiment
