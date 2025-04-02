from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from functions.sentiment_analysis_functions import get_user_sentiment
from pymongo import MongoClient

sentiment_bp = Blueprint("api/sentiment", __name__)

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["your_database"]
mental_status_collection = db["mental_status"]

@sentiment_bp.route("/analyze_sentiment", methods=["GET"])
def analyze_sentiment():
    """
    API to calculate and return the user's sentiment for a given date.
    """
    user_id = request.args.get("user_id")
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))

    sentiment_score = get_user_sentiment(user_id, date_str)

    return jsonify({"date": date_str, "sentiment_score": sentiment_score})

@sentiment_bp.route("/sentiment_trend", methods=["GET"])
def get_sentiment_trend():
    """
    API to get the sentiment trend for the past N days.
    """
    user_id = request.args.get("user_id")
    days = int(request.args.get("days", 7))  # Default to past 7 days

    today = datetime.now()
    trend_data = []

    for i in range(days):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        sentiment_record = mental_status_collection.find_one({"user_id": user_id, "date": date_str})

        trend_data.append({
            "date": date_str,
            "sentiment_score": sentiment_record["sentiment_score"] if sentiment_record else 0
        })

    return jsonify({"trend": trend_data})
