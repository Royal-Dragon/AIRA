from flask import Blueprint, request, jsonify
from database.models import get_database
from bson import ObjectId
from werkzeug.security import generate_password_hash
from routes.auth import verify_jwt_token
import logging

logger = logging.getLogger(__name__)

user_bp = Blueprint("user", __name__, url_prefix="/api/user")

@user_bp.route("/profile", methods=["GET"])
def get_profile():
    """Retrieve user profile safely."""
    user_id = verify_jwt_token(request)
    if not user_id:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    try:
        db = get_database()
        users_collection = db["users"]
        user = users_collection.find_one({"_id": ObjectId(user_id)}, {"password": 0})
    except Exception as e:
        logger.error(f"Database error while retrieving profile: {e}")
        return jsonify({"error": "Database error", "details": str(e)}), 500

    if not user:
        return jsonify({"error": "User not found"}), 404

    user["user_id"] = str(user["_id"])
    del user["_id"]

    logger.info(f"Profile retrieved for user {user_id}")
    return jsonify({"profile": user}), 200

@user_bp.route("/update", methods=["PUT"])
def update_profile():
    """Update user profile safely."""
    user_id = verify_jwt_token(request)
    if not user_id:
        return jsonify({"error": "Unauthorized. Please log in."}), 401

    data = request.json
    new_username = data.get("username")
    new_email = data.get("email")
    new_password = data.get("password")

    if not new_username or not new_email:
        return jsonify({"error": "Username and email are required."}), 400

    try:
        db = get_database()
        users_collection = db["users"]

        # Check if email already exists
        existing_user = users_collection.find_one({"email": new_email, "_id": {"$ne": ObjectId(user_id)}})
        if existing_user:
            return jsonify({"error": "Email is already in use."}), 400

        update_data = {
            "username": new_username,
            "email": new_email
        }

        # Handle password update
        if new_password:
            update_data["password"] = generate_password_hash(new_password)

        result = users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
    except Exception as e:
        logger.error(f"Database error while updating profile: {e}")
        return jsonify({"error": "Database error", "details": str(e)}), 500

    if result.modified_count == 0:
        return jsonify({"message": "No changes made or user not found."}), 400

    logger.info(f"Profile updated for user {user_id}")
    return jsonify({"message": "Profile updated successfully"}), 200
