from flask import Blueprint, request, jsonify, make_response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import uuid
from config import JWT_SECRET_KEY
from database.models import get_collection
from flask_cors import CORS
from extensions import oauth
from functions.auth_functions import (
    generate_token, 
    decode_token, 
    verify_jwt_token
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Enable CORS for this blueprint
CORS(auth_bp,supports_credentials=True, resources={r"/*": {"origins": "http://localhost:5173"}})

# Get collections
users_collection = get_collection("users")
sessions_collection = get_collection("sessions")
auth_codes_collection = get_collection("auth_codes")

# Routes
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    if not all([username, email, password]):
        return jsonify({"error": "All fields are required"}), 400
    if users_collection.find_one({"email": email}):
        return jsonify({"error": "User already exists"}), 409
    hashed_password = generate_password_hash(password)
    user_data = {
        "username": username,
        "email": email,
        "password": hashed_password,
        "created_at": datetime.datetime.utcnow()
    }
    result = users_collection.insert_one(user_data)
    return jsonify({"username": username, "message": "User registered successfully"}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    if not all([email, password]):
        return jsonify({"error": "Email and password are required"}), 400
    user = users_collection.find_one({"email": email})
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401
    session_id = str(uuid.uuid4())
    session_expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    session_data = {
        "user_id": str(user["_id"]),
        "session_id": session_id,
        "login_time": datetime.datetime.utcnow(),
        "expires_at": session_expires_at,
        "active": True
    }
    sessions_collection.insert_one(session_data)
    access_token = generate_token(user["_id"], session_id, datetime.timedelta(minutes=15))
    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": session_id,
        "user": {"username": user["username"], "email": user["email"]}
    }), 200

@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    data = request.json
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400
    session = sessions_collection.find_one({"session_id": refresh_token, "active": True})
    if not session or session["expires_at"] < datetime.datetime.utcnow():
        return jsonify({"error": "Invalid or expired refresh token"}), 401
    access_token = generate_token(session["user_id"], session["session_id"], datetime.timedelta(minutes=15))
    return jsonify({"access_token": access_token}), 200

@auth_bp.route("/logout", methods=["POST"])
def logout():
    auth_header = request.headers.get("Authorization")
    if not auth_header or "Bearer" not in auth_header:
        return jsonify({"error": "Authorization header is missing or invalid"}), 400
    token = auth_header.split("Bearer ")[1]
    decoded_token = decode_token(token, verify_exp=False)
    if not decoded_token:
        return jsonify({"error": "Invalid token"}), 401
    session_id = decoded_token.get("session_id")
    sessions_collection.delete_one({"session_id": session_id})
    return jsonify({"message": "Logout successful"}), 200

@auth_bp.route("/protected", methods=["GET"])
def protected():
    user_id = verify_jwt_token(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    user = users_collection.find_one({"_id": user_id})
    return jsonify({"message": f"Welcome, {user['username']}!"}), 200

# Google OAuth Routes
@auth_bp.route('/google/login')
def google_login():
    redirect_uri = url_for('auth.google_callback', _external=True)
    state = str(uuid.uuid4())
    nonce = str(uuid.uuid4())
    session['oauth_state'] = state
    session['oauth_nonce'] = nonce
    return oauth.google.authorize_redirect(redirect_uri, state=state, nonce=nonce)

@auth_bp.route('/google/callback')
def google_callback():
    if 'state' not in request.args or request.args['state'] != session.pop('oauth_state', None):
        return "Invalid state parameter", 400
    token = oauth.google.authorize_access_token()
    nonce = session.pop('oauth_nonce', None)
    if not nonce:
        return "Nonce not found in session", 400
    user_info = oauth.google.parse_id_token(token, nonce=nonce)
    user = users_collection.find_one({"email": user_info['email']})
    if user:
        session_id = str(uuid.uuid4())
        session_expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        session_data = {
            "user_id": str(user["_id"]),
            "session_id": session_id,
            "login_time": datetime.datetime.utcnow(),
            "expires_at": session_expires_at,
            "active": True
        }
        sessions_collection.insert_one(session_data)
        access_token = generate_token(user["_id"], session_id, datetime.timedelta(minutes=15))
        username = user["username"]
        email = user["email"]
    else:
        username = user_info['name']
        email = user_info['email']
        user_data = {
            "username": username,
            "email": email,
            "password": None,
            "created_at": datetime.datetime.utcnow()
        }
        result = users_collection.insert_one(user_data)
        user_id = result.inserted_id
        session_id = str(uuid.uuid4())
        session_expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=7)
        session_data = {
            "user_id": str(user_id),
            "session_id": session_id,
            "login_time": datetime.datetime.utcnow(),
            "expires_at": session_expires_at,
            "active": True
        }
        sessions_collection.insert_one(session_data)
        access_token = generate_token(user_id, session_id, datetime.timedelta(minutes=15))

    # Store the one-time code in MongoDB
    code = str(uuid.uuid4())
    code_data = {
        "code": code,
        "access_token": access_token,
        "refresh_token": session_id,
        "user": {"username": username, "email": email},
        "created_at": datetime.datetime.utcnow(),
        "expires_at": datetime.datetime.utcnow() + datetime.timedelta(minutes=5)  # Code expires in 5 minutes
    }
    auth_codes_collection.insert_one(code_data)
    print(f"Stored code in DB: {code}, Tokens: {code_data}")  # Debug log

    frontend_url = f"http://localhost:5173/auth/callback?code={code}"
    return redirect(frontend_url)

@auth_bp.route('/exchange_code', methods=["POST"])
def exchange_code():
    data = request.json
    code = data.get("code")
    print(f"Received code for exchange: {code}")  # Debug log

    # Find the code in the database
    code_entry = auth_codes_collection.find_one({"code": code})
    if not code_entry:
        print("Code not found in database")
        return jsonify({"error": "Invalid code"}), 400

    # Check if the code has expired
    if code_entry["expires_at"] < datetime.datetime.utcnow():
        print("Code has expired")
        auth_codes_collection.delete_one({"code": code})  # Clean up expired code
        return jsonify({"error": "Code has expired"}), 400

    # Extract tokens and user info
    tokens = {
        "access_token": code_entry["access_token"],
        "refresh_token": code_entry["refresh_token"],
        "user": code_entry["user"]
    }

    # Delete the code from the database (one-time use)
    auth_codes_collection.delete_one({"code": code})
    print(f"Returning tokens: {tokens}")  # Debug log

    return jsonify(tokens), 200