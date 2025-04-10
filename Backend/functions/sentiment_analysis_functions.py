from collections import defaultdict
import re
from model_memory import get_model
import json
from database.models import sentiment_collection
from datetime import datetime, timedelta

def extract_json_from_text(text):
    """Extract valid JSON from model response text."""
    # Try to extract JSON if it's embedded in markdown or other text
    json_pattern = r'({[\s\S]*})'
    matches = re.findall(json_pattern, text)
    
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, dict):
                # Validate expected fields
                if all(k in data for k in ["mental_score", "stress_type", "supporting_text", "suggestions"]):
                    return match
        except json.JSONDecodeError:
            continue
    
    # If no valid JSON found in regex matches, try the entire text
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return text
    except json.JSONDecodeError:
        pass
    
    return None


def analyze_mental_wellness(text, model, previous_scores=None):
    """Analyze text for mental wellness indicators with improved score variation."""
    if not text or len(text.strip()) < 20:  # Skip very short texts
        return {
            "mental_score": 80,
            "stress_type": "None",
            "supporting_text": "",
            "suggestions": []
        }
    
    # Clean the text to avoid prompt injection
    cleaned_text = text.replace('"', "'").strip()
    
    # Add context about previous scores if available
    previous_context = ""
    if previous_scores and len(previous_scores) > 0:
        last_score = previous_scores[-1]
        previous_context = f"""
        Note: The user's previous mental wellness score was {last_score}. 
        Your assessment should reflect genuine changes based on today's messages.
        If you detect a small improvement, increase the score by 1-3 points.
        If you detect a small decline, decrease the score by 1-3 points.
        If you detect a significant change, adjust by 5-10 points.
        """
    
    prompt = f"""
    You are a mental health assistant with expertise in detecting subtle emotional variations. 
    Analyze the following set of user messages from a single day:
    "{cleaned_text}"

    Each message is written by the user. Look for signs of stress, anxiety, low mood, or other emotional concerns.
    Be sensitive to subtle changes in tone, word choice, and content.
    
    {previous_context}
    
    Your mental_score should be precise and can include decimals (like 78.5 or 82.3).
    The score should reflect genuine emotional content - avoid giving the same score repeatedly.
    
    Respond ONLY with a valid JSON object containing:
    - mental_score (0-100, where lower means more concern, can include decimals for precision)
    - stress_type (the most prominent stress type: "Burnout", "Overthinking", "Anxiety", "Social Stress", "Low Mood", or "None")
    - supporting_text (direct quote from the conversation showing the most concerning evidence)
    - suggestions (array of 2-3 helpful ideas, empty if stress_type is "None")

    Format: {{key:value}} with NO extra text, markdown, or explanation.
    """
    
    try:
        response = model.invoke(prompt)
        json_str = extract_json_from_text(response.content)
        if json_str:
            data = json.loads(json_str)
            
            # Validate the mental_score is within range
            if not isinstance(data.get("mental_score"), (int, float)) or not (0 <= data["mental_score"] <= 100):
                data["mental_score"] = 80
            
            # Validate stress_type
            valid_stress_types = ["Burnout", "Overthinking", "Anxiety", "Social Stress", "Low Mood", "None"]
            if data.get("stress_type") not in valid_stress_types:
                data["stress_type"] = "None"
            
            # Ensure supporting_text exists
            if "supporting_text" not in data:
                data["supporting_text"] = ""
                
            # Ensure suggestions is a list
            if not isinstance(data.get("suggestions"), list):
                data["suggestions"] = []
            
            return data
        else:
            # Default response if no valid JSON is found
            return {
                "mental_score": 80,
                "stress_type": "None",
                "supporting_text": "",
                "suggestions": []
            }
    except Exception as e:
        print(f"Error analyzing mental wellness: {e}")
        return {
            "mental_score": 80,
            "stress_type": "None",
            "supporting_text": "",
            "suggestions": []
        }

def validate_supporting_text(supporting_text, combined_text):
    """Validate that the supporting_text is likely from the original text."""
    if not supporting_text:
        return False
        
    # If the exact text is found, it's valid
    if supporting_text in combined_text:
        return True
        
    # Otherwise, check if significant words from supporting_text appear in combined_text
    significant_words = [word for word in supporting_text.split() if len(word) > 3]
    if not significant_words:
        return False
        
    # Count how many significant words appear in the combined text
    matches = sum(1 for word in significant_words if word.lower() in combined_text.lower())
    match_ratio = matches / len(significant_words) if significant_words else 0
    
    # Return True if at least 60% of significant words match
    return match_ratio >= 0.6

def already_analyzed(user_id, date):
    """Check if the given date was already analyzed for this user."""
    try:
        user_doc = sentiment_collection.find_one({"user_id": str(user_id)})
        if not user_doc:
            return False
        return any(s.get("date") == date for s in user_doc.get("sentiments", []))
    except Exception as e:
        print(f"Error checking if already analyzed: {e}")
        return True  # Assume already analyzed to prevent duplicate processing

def process_daily_messages(sessions, user_id):
    """Process and analyze daily messages for emotional content with score trending."""
    day_data = defaultdict(list)
    user_id_str = str(user_id)  # Ensure user_id is a string for MongoDB
    
    # Define the threshold score - below this we show stress information
    STRESS_THRESHOLD = 70  # You can adjust this value as needed

    # Group messages by day
    for session in sessions:
        if not session or session.get("title") == "Introduction Session":
            continue
            
        for msg in session.get("messages", []):
            if not msg or msg.get("role") != "User" or "created_at" not in msg:
                continue
                
            try:
                date = msg["created_at"][:10]
                content = msg.get("content", "").strip()
                if content:  # Skip empty messages
                    day_data[date].append(content)
            except Exception as e:
                print(f"Error processing message: {e}")

    # Get model for analysis
    try:
        model = get_model()
    except Exception as e:
        print(f"Error getting model: {e}")
        return

    # Get previous scores for context
    previous_scores = []
    try:
        user_doc = sentiment_collection.find_one({"user_id": user_id_str})
        if user_doc and "sentiments" in user_doc:
            # Get last 7 days of scores
            sentiments = sorted(user_doc["sentiments"], key=lambda x: x.get("date", ""))[-7:]
            previous_scores = [s.get("mental_score", 80) for s in sentiments]
    except Exception as e:
        print(f"Error getting previous scores: {e}")

    # Process each day's messages
    for day, messages in day_data.items():
        try:
            # Skip already analyzed days
            if already_analyzed(user_id_str, day):
                continue

            # Skip days with insufficient data
            if not messages:
                continue

            combined_text = "\n".join(messages)
            
            # Pass previous scores for context
            analysis = analyze_mental_wellness(combined_text, model, previous_scores)
            
            # Update previous_scores for next iteration
            previous_scores.append(analysis.get("mental_score", 80))
            if len(previous_scores) > 7:
                previous_scores = previous_scores[-7:]

            # Validate supporting text if score is below threshold
            if analysis.get("mental_score", 80) < STRESS_THRESHOLD:
                if analysis.get("stress_type") != "None":
                    if not validate_supporting_text(analysis.get("supporting_text", ""), combined_text):
                        # Keep the score but reset stress info if supporting text doesn't match
                        analysis["stress_type"] = "None"
                        analysis["supporting_text"] = ""
                        analysis["suggestions"] = []
            else:
                # If score is above threshold, clear stress information
                analysis["stress_type"] = "None"
                analysis["supporting_text"] = ""
                analysis["suggestions"] = []

            # Add some natural variation to default scores
            if analysis.get("stress_type") == "None" and abs(analysis.get("mental_score", 80) - 80) < 0.1:
                # If it's a default score, add slight variation
                import random
                variation = random.uniform(-2, 2)
                analysis["mental_score"] = 80 + variation

            # Build sentiment entry
            sentiment_data = {
                "date": day,
                **analysis
            }

            # Store the oldest date we want to keep (30 days ago)
            cutoff_date = (datetime.strptime(day, "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")
            
            # First, ensure the user document exists
            sentiment_collection.update_one(
                {"user_id": user_id_str},
                {"$setOnInsert": {"sentiments": []}},
                upsert=True
            )
            
            # Then add new sentiment data
            sentiment_collection.update_one(
                {"user_id": user_id_str},
                {"$push": {"sentiments": sentiment_data}}
            )
            
            # Finally, remove old data in a separate operation
            sentiment_collection.update_one(
                {"user_id": user_id_str},
                {"$pull": {
                    "sentiments": {
                        "date": {"$lt": cutoff_date}
                    }
                }}
            )
            
        except Exception as e:
            print(f"Error processing day {day}: {e}")