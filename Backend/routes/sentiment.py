from flask import Blueprint, request, jsonify
from functions.sentiment_analysis_functions import process_daily_messages
from database.models import get_collection
from bson import ObjectId
from database.models import sentiment_collection
from datetime import datetime,timedelta

sentiment_bp = Blueprint("sentiment", __name__, url_prefix="/api/sentiment")

@sentiment_bp.route('/analyze', methods=['GET'])
def analyze():
    user_id = request.args.get("user_id")
    # print("\n user id from sentimaent ",user_id)

    chat_history=get_collection("chat_history")
    user_chat_history = chat_history.find_one({"user_id": ObjectId(user_id)})
    # print("\n user chat history ",user_chat_history)  # 

    if not user_chat_history:
        return jsonify({"message": "No chat history found"}), 404
    
    sessions = user_chat_history.get("sessions", [])

    # print("\n\n user sessions history ",sessions)
    result = process_daily_messages(sessions,user_id)
    return jsonify({"message": "Sentiment analysis completed successfully."}), 200

@sentiment_bp.route('/get_sentiments', methods=['GET'])
def get_sentiments():
    """
    Get sentiment data for a user over time.
    
    Query parameters:
    - user_id: required, the id of the user
    - days: optional, number of days to look back (default: 30)
    - format: optional, 'full' or 'chart' (default: 'chart')
    
    Returns:
    - For 'chart' format: Array of {date, mental_score} objects
    - For 'full' format: All sentiment data including stress types and suggestions
    """
    try:
        # Get and validate user_id
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "Missing required parameter: user_id"}), 400
        
        # Get optional parameters with defaults
        days_back = int(request.args.get('days', 30))
        data_format = request.args.get('format', 'chart')
        
        # Calculate the cutoff date
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        # Get user document with sentiments
        user_doc = sentiment_collection.find_one({"user_id": str(user_id)})
        if not user_doc or 'sentiments' not in user_doc:
            return jsonify({"data": []}), 200
        
        # Filter sentiments by date
        sentiments = [s for s in user_doc.get('sentiments', []) if s.get('date', '') >= cutoff_date]
        
        # Sort sentiments by date
        sentiments.sort(key=lambda x: x.get('date', ''))
        
        if data_format == 'chart':
            # Format for charting (just date and score)
            chart_data = [
                {
                    "date": s.get('date'),
                    "mental_score": s.get('mental_score', 80),
                    "stress_type": s.get('stress_type', 'None'),
                    "supporting_text": s.get('supporting_text', ''),
                    "suggestions": s.get('suggestions', [])
                }
                for s in sentiments
            ]
            return jsonify({"data": chart_data}), 200
            
        else:  # 'full' format
            # Return all sentiment data
            return jsonify({"data": sentiments}), 200
            
    except Exception as e:
        print(f"Error retrieving sentiment data: {e}")
        return jsonify({"error": "Failed to retrieve sentiment data", "details": str(e)}), 500

@sentiment_bp.route('/summary', methods=['GET'])
def get_sentiment_summary():
    """
    Get a summary of sentiment data for a user.
    
    Query parameters:
    - user_id: required, the id of the user
    - days: optional, number of days to look back (default: 30)
    - threshold: optional, score threshold for counting stress types (default: 70)
    
    Returns:
    - average_score: Average mental score over the period
    - stress_types: Frequency count of different stress types (only below threshold)
    - trend: 'improving', 'declining', or 'stable'
    - below_threshold_days: Count of days below threshold
    - total_days: Total days with data
    """
    try:
        # Get and validate user_id
        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "Missing required parameter: user_id"}), 400
        
        # Get optional parameters with defaults
        days_back = int(request.args.get('days', 30))
        threshold = float(request.args.get('threshold', 70))
        
        # Calculate the cutoff date
        cutoff_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        # Get user document with sentiments
        user_doc = sentiment_collection.find_one({"user_id": str(user_id)})
        if not user_doc or 'sentiments' not in user_doc:
            return jsonify({
                "average_score": 80,
                "stress_types": {},
                "trend": "stable",
                "below_threshold_days": 0,
                "total_days": 0
            }), 200
        
        # Filter and sort sentiments by date
        sentiments = [s for s in user_doc.get('sentiments', []) if s.get('date', '') >= cutoff_date]
        sentiments.sort(key=lambda x: x.get('date', ''))
        
        # If no data, return defaults
        if not sentiments:
            return jsonify({
                "average_score": 80,
                "stress_types": {},
                "trend": "stable",
                "below_threshold_days": 0,
                "total_days": 0
            }), 200
        
        # Calculate average score
        scores = [s.get('mental_score', 80) for s in sentiments]
        average_score = sum(scores) / len(scores) if scores else 80
        
        # Count days below threshold
        below_threshold_days = sum(1 for score in scores if score < threshold)
        
        # Count stress types (only for scores below threshold)
        stress_types = {}
        for s in sentiments:
            if s.get('mental_score', 80) < threshold:
                stress_type = s.get('stress_type', 'None')
                if stress_type != 'None':
                    stress_types[stress_type] = stress_types.get(stress_type, 0) + 1
        
        # Determine trend (compare first and last week if enough data)
        trend = "stable"
        if len(scores) >= 7:
            first_week = scores[:min(7, len(scores)//2)]  # First half of available data, up to 7 days
            last_week = scores[-min(7, len(scores)//2):]  # Last half of available data, up to 7 days
            first_avg = sum(first_week) / len(first_week)
            last_avg = sum(last_week) / len(last_week)
            
            # More nuanced trend detection
            diff = last_avg - first_avg
            if diff > 5:
                trend = "improving"
            elif diff < -5:
                trend = "declining"
            elif diff > 2:
                trend = "slightly_improving"
            elif diff < -2:
                trend = "slightly_declining"
        
        # Calculate most recent change
        recent_change = None
        if len(scores) >= 2:
            recent_change = scores[-1] - scores[-2]
        
        # Find most frequent stress type
        primary_stress = None
        if stress_types:
            primary_stress = max(stress_types.items(), key=lambda x: x[1])[0]
        
        return jsonify({
            "average_score": round(average_score, 1),
            "stress_types": stress_types,
            "trend": trend,
            "below_threshold_days": below_threshold_days,
            "total_days": len(scores),
            "threshold": threshold,
            "recent_change": round(recent_change, 1) if recent_change is not None else None,
            "primary_stress_type": primary_stress
        }), 200
            
    except Exception as e:
        print(f"Error retrieving sentiment summary: {e}")
        return jsonify({"error": "Failed to retrieve sentiment summary", "details": str(e)}), 500
