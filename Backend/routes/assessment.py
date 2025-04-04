from flask import Blueprint, request, jsonify
import datetime
from routes.auth import verify_jwt_token
from database.models import question_collection, get_collection
from bson.objectid import ObjectId
from functions.assessment_functions import cleanup_expired_sessions, ongoing_assessments, calculate_score

assessment_bp = Blueprint("assessment", __name__, url_prefix="/api/assessment")

brain_collection = get_collection("aira_brain")

SESSION_EXPIRY_MINUTES = 10  # Expire sessions after 10 minutes

@assessment_bp.route("/start", methods=["POST"])
def start_assessment():
    """Start the assessment and ask the first question."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    if question_collection is None:
        return jsonify({"error": "Database error: question_collection is not initialized."}), 500

    cleanup_expired_sessions()

    # Verify user exists in brain_collection
    try:
        # Convert user_id to ObjectId for lookup
        user_obj_id = ObjectId(user_id)
        user_doc = brain_collection.find_one({"user_id": user_obj_id})
        
        if not user_doc:
            return jsonify({"error": "User profile not found. Please create a profile first."}), 404
    except Exception as e:
        print(f"Error checking user document: {e}")
        return jsonify({"error": "Database error while checking user document."}), 500

    # Fetch all available categories from the database
    try:
        categories = question_collection.distinct("category")
    except Exception as e:
        print(f"Error fetching distinct categories: {e}")
        return jsonify({"error": "Error fetching categories from the database."}), 500

    # Initialize user assessment session
    ongoing_assessments[user_id] = {"category": None, "question_ids": [], "answers": [], "timestamp": datetime.datetime.utcnow()}

    # Return categories as options for the first question
    first_question = "Which area would you like to assess today?"
    
    return jsonify({
        "question": first_question,
        "options": categories,
        "info": "Please select one of the options above to begin your assessment."
    }), 200

@assessment_bp.route("/next", methods=["POST"])
def next_question():
    """Process the user's answer and provide the next question or store results."""
    data = request.json
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid token"}), 401
    
    token = auth_header.split(" ")[1]
    user_id = verify_jwt_token(token)
    answer = data.get("answer")

    if not user_id or answer is None:
        return jsonify({"error": "Invalid request. Ensure user is authenticated and answer is provided."}), 400

    if question_collection is None:
        return jsonify({"error": "Database connection error: question_collection is not initialized."}), 500

    cleanup_expired_sessions()

    if user_id not in ongoing_assessments:
        return jsonify({"error": "Session expired or assessment not started. Please restart."}), 400

    user_data = ongoing_assessments[user_id]

    if user_data["category"] is None:
        try:
            # Get all categories
            categories = question_collection.distinct("category")
            
            # Check if answer is a valid index for the categories list
            try:
                category_index = int(answer)
                if not (0 <= category_index < len(categories)):
                    return jsonify({"error": f"Invalid option. Please select a number between 0 and {len(categories)-1}."}), 400
                
                selected_category = categories[category_index]
            except ValueError:
                # If not an index, try direct matching (for backward compatibility)
                answer_lower = answer.lower()
                categories_lower = [cat.lower() for cat in categories]
                
                if answer_lower in categories_lower:
                    selected_category = categories[categories_lower.index(answer_lower)]
                else:
                    return jsonify({"error": f"Invalid category. Please select a valid option."}), 400
            
            # Set the selected category
            user_data["category"] = selected_category
            user_data["question_ids"] = []
            user_data["answers"] = []
            user_data["timestamp"] = datetime.datetime.utcnow()

            # Get the first question for the selected category
            first_question_doc = question_collection.find_one({"category": selected_category})
            if not first_question_doc:
                return jsonify({"error": "No questions found for this category in the database."}), 500

            user_data["question_ids"].append(first_question_doc["_id"])
            return jsonify({"question": first_question_doc["question_text"], "options": first_question_doc.get("options")}), 200
            
        except Exception as e:
            print(f"Error processing category selection: {e}")
            return jsonify({"error": "Error processing category selection."}), 500

    try:
        score = int(answer)
        last_question_id = user_data["question_ids"][-1]
        last_question = question_collection.find_one({"_id": last_question_id})

        if not last_question or 'options' not in last_question:
            return jsonify({"error": "Invalid question or options not found."}), 500

        if not (0 <= score < len(last_question['options'])):
            return jsonify({"error": "Response must be a valid option index."}), 400

        user_data["answers"].append(score)
        user_data["timestamp"] = datetime.datetime.utcnow()

    except ValueError:
        return jsonify({"error": "Invalid response format. Answer should be the index of your choice (0-n)."}), 400

    category = user_data["category"]
    asked_question_ids = user_data["question_ids"]

    next_question_doc = question_collection.find_one({"category": category, "_id": {"$nin": asked_question_ids}})
    if not next_question_doc:
        # Assessment completed, calculate and store results
        score, level = calculate_score(user_data["answers"], user_data["question_ids"])

        # Prepare assessment result for storage
        assessment = {
            "category": user_data["category"],
            "mental_score": score,
            "level": level,
            "timestamp": datetime.datetime.utcnow().isoformat()
        }

        # Look up the user by user_id field, not _id
        try:
            user_obj_id = ObjectId(user_id)
            
            # First, check if the assessments field exists
            user_doc = brain_collection.find_one({"user_id": user_obj_id})
            
            if not user_doc:
                return jsonify({"error": "User profile not found. Please create a profile first."}), 404
                
            # Update strategy depends on whether assessments field exists
            if "assessments" in user_doc:
                # Assessments field exists, use $push
                update_result = brain_collection.update_one(
                    {"user_id": user_obj_id},
                    {"$push": {"assessments": assessment}}
                )
            else:
                # Assessments field doesn't exist, use $set with new array
                update_result = brain_collection.update_one(
                    {"user_id": user_obj_id},
                    {"$set": {"assessments": [assessment]}}
                )
                
            if update_result.matched_count == 0:
                return jsonify({"error": "Failed to update user document."}), 500
                
        except Exception as e:
            print(f"Error storing assessment result: {e}")
            return jsonify({"error": f"An error occurred while storing the assessment result: {str(e)}"}), 500

        # Prepare result for response
        result = {
            "user_id": str(user_obj_id),
            "category": user_data["category"],
            "mental_score": score,
            "level": level,
            "timestamp": assessment["timestamp"]
        }

        # Remove session after completion
        del ongoing_assessments[user_id]

        return jsonify(result), 200

    user_data["question_ids"].append(next_question_doc["_id"])
    return jsonify({"question": next_question_doc["question_text"], "options": next_question_doc.get("options")}), 200

# @assessment_bp.route("/categories", methods=["GET"])
# def get_categories():
#     """Get all available assessment categories."""
#     try:
#         if question_collection is None:
#             return jsonify({"error": "Database connection error: question_collection is not initialized."}), 500
#         valid_categories = question_collection.distinct("category")
#         return jsonify({"categories": valid_categories, "count": len(valid_categories)}), 200
#     except Exception as e:
#         print(f"Error fetching distinct categories: {e}")
#         return jsonify({"error": "Error fetching categories from the database."}), 500