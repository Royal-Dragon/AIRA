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
    """Start the assessment with a broad screening question."""
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
        user_obj_id = ObjectId(user_id)
        user_doc = brain_collection.find_one({"user_id": user_obj_id})
        if not user_doc:
            return jsonify({"error": "User profile not found. Please create a profile first."}), 404
    except Exception as e:
        print(f"Error checking user document: {e}")
        return jsonify({"error": "Database error while checking user document."}), 500

    # Initialize user assessment session
    ongoing_assessments[user_id] = {
        "current_category": None,
        "potential_categories": [],
        "question_ids": [],
        "answers": [],
        "timestamp": datetime.datetime.utcnow()
    }

    # First screening question to identify potential areas
    first_question = "Over the past two weeks, how often have you been bothered by any of the following problems?"
    screening_questions = [
        "Feeling down, depressed, or hopeless",
        "Little interest or pleasure in doing things",
        "Feeling nervous, anxious, or on edge",
        "Not being able to stop or control worrying"
    ]
    
    return jsonify({
        "question": first_question,
        "options": screening_questions,
        "info": "Please select all that apply to you (comma-separated numbers, e.g. '0,2')",
        "is_screening": True
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

    # Handle screening phase (first question)
    if not user_data["potential_categories"] and "is_screening" in data:
        try:
            # Parse selected options (comma-separated numbers)
            selected_indices = [int(idx.strip()) for idx in answer.split(",") if idx.strip().isdigit()]
            
            # Map selections to categories
            category_mapping = {
                0: "Depression",
                1: "Depression",
                2: "Anxiety",
                3: "Anxiety"
            }
            
            # Get unique categories from selections
            selected_categories = list({category_mapping[idx] for idx in selected_indices if idx in category_mapping})
            
            if not selected_categories:
                return jsonify({"error": "No valid categories selected. Please try again."}), 400
                
            user_data["potential_categories"] = selected_categories
            user_data["current_category"] = selected_categories[0]  # Start with first category
            
            # Get first question for the selected category
            first_question = question_collection.find_one({"category": user_data["current_category"]})
            if not first_question:
                return jsonify({"error": "No questions found for this category."}), 404
                
            user_data["question_ids"].append(first_question["_id"])
            return jsonify({
                "question": first_question["question_text"],
                "options": first_question.get("options", []),
                "current_category": user_data["current_category"],
                "remaining_categories": user_data["potential_categories"][1:]
            }), 200
            
        except Exception as e:
            print(f"Error processing screening response: {e}")
            return jsonify({"error": "Invalid screening response format."}), 400

    # Handle regular question answers
    try:
        # Validate answer is within options range
        last_question_id = user_data["question_ids"][-1]
        last_question = question_collection.find_one({"_id": last_question_id})
        
        if not last_question or 'options' not in last_question:
            return jsonify({"error": "Invalid question or options not found."}), 500

        try:
            answer_index = int(answer)
            if not (0 <= answer_index < len(last_question['options'])):
                return jsonify({"error": f"Invalid option index. Please select between 0-{len(last_question['options'])-1}."}), 400
        except ValueError:
            return jsonify({"error": "Invalid answer format. Please provide the option index as a number."}), 400

        # Store answer
        user_data["answers"].append(answer_index)
        user_data["timestamp"] = datetime.datetime.utcnow()

    except Exception as e:
        print(f"Error processing answer: {e}")
        return jsonify({"error": "Error processing your answer."}), 500

    # Get next question in current category
    next_question_doc = question_collection.find_one({
        "category": user_data["current_category"],
        "_id": {"$nin": user_data["question_ids"]}
    })

    if next_question_doc:
        user_data["question_ids"].append(next_question_doc["_id"])
        return jsonify({
            "question": next_question_doc["question_text"],
            "options": next_question_doc.get("options", []),
            "current_category": user_data["current_category"],
            "remaining_categories": user_data["potential_categories"][1:]
        }), 200
    else:
        # Current category completed - check if more categories to assess
        if len(user_data["potential_categories"]) > 1:
            # Move to next category
            user_data["potential_categories"].pop(0)
            user_data["current_category"] = user_data["potential_categories"][0]
            user_data["question_ids"] = []  # Reset for new category
            
            first_question = question_collection.find_one({"category": user_data["current_category"]})
            if not first_question:
                return jsonify({"error": "No questions found for next category."}), 404
                
            user_data["question_ids"].append(first_question["_id"])
            return jsonify({
                "question": first_question["question_text"],
                "options": first_question.get("options", []),
                "current_category": user_data["current_category"],
                "remaining_categories": user_data["potential_categories"][1:]
            }), 200
        else:
            # All categories completed - calculate scores
            try:
                score, level = calculate_score(user_data["answers"], user_data["question_ids"])
                
                assessment = {
                    "categories_assessed": user_data["potential_categories"],
                    "mental_score": score,
                    "level": level,
                    "answers": user_data["answers"],
                    "timestamp": datetime.datetime.utcnow().isoformat()
                }

                user_obj_id = ObjectId(user_id)
                update_result = brain_collection.update_one(
                    {"user_id": user_obj_id},
                    {"$push": {"assessments": assessment}},
                    upsert=True
                )
                
                if update_result.matched_count == 0 and not update_result.upserted_id:
                    return jsonify({"error": "Failed to store assessment results."}), 500
                    
                # Prepare detailed response
                result = {
                    "user_id": str(user_obj_id),
                    "categories": user_data["potential_categories"],
                    "score": score,
                    "level": level,
                    "timestamp": assessment["timestamp"]
                }

                del ongoing_assessments[user_id]
                return jsonify(result), 200
                
            except Exception as e:
                print(f"Error calculating/storing results: {e}")
                return jsonify({"error": "Error processing assessment results."}), 500