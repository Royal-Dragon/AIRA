import datetime
from database.models import question_collection

SESSION_EXPIRY_MINUTES = 10  # Expire sessions after 10 minutes

ongoing_assessments = {}

def cleanup_expired_sessions():
    """Remove expired sessions based on SESSION_EXPIRY_MINUTES."""
    now = datetime.datetime.utcnow()
    expired_users = [
        user_id for user_id, data in ongoing_assessments.items()
        if (now - data["timestamp"]).total_seconds() > SESSION_EXPIRY_MINUTES * 60
    ]
    for user_id in expired_users:
        del ongoing_assessments[user_id]

def calculate_score(answers, question_ids):
    """Calculate the user's score based on their responses."""
    total_score = 0
    for question_id, answer in zip(question_ids, answers):
        question = question_collection.find_one({"_id": question_id})
        if not question:
            print(f"Warning: Question not found in DB: {question_id}")
            continue
        try:
            score = question['scores'][int(answer)]
            total_score += score
        except (IndexError, ValueError) as e:
            print(f"Error calculating score for question {question_id}: {e}")
            continue
    if total_score < 5:
        level = "Low Stress"
    elif total_score < 10:
        level = "Moderate Stress"
    else:
        level = "High Stress"
    return total_score, level