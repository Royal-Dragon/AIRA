from flask import Blueprint, request, jsonify
import logging
from database.models import get_collection
from datetime import datetime
import uuid
from bson import ObjectId

logger = logging.getLogger(__name__)

visionboard_bp = Blueprint("visionboard", __name__, url_prefix="/api/visionboard")

@visionboard_bp.route("/add_custom_goal", methods=["POST"])
def add_custom_goal():
    data = request.get_json()
    user_id = data.get("user_id")
    goal_text = data.get("goal")

    if not user_id or not goal_text:
        return jsonify({"error": "Missing required fields"}), 400

    brain_collection = get_collection("aira_brain")

    try:
        user_object_id = ObjectId(user_id)
    except Exception as e:
        return jsonify({"error": "Invalid user_id format"}), 400

    # 1. Find the user in the Brain collection
    user = brain_collection.find_one({"user_id": user_object_id})
    if not user:
        return jsonify({"error": "User not found in AIRA's Brain"}), 404

    # 2. Check for duplicates
    existing_goals = [g["data"].strip().lower() for g in user.get("goals", [])]
    if goal_text.strip().lower() in existing_goals:
        return jsonify({"message": "Goal already exists."}), 200

    # 3. Add the new user-submitted goal
    new_goal = {
        "response_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow(),
        "data": goal_text.strip()
    }

    brain_collection.update_one(
        {"user_id": user_object_id},
        {"$push": {"goals": new_goal}}
    )

    return jsonify({"message": "Custom goal added to AIRA's Brain.", "goal": goal_text}), 200
