import datetime
import jwt
from config import JWT_SECRET_KEY

# Token generation and decoding
def generate_token(user_id, session_id, expiration_delta):
    payload = {
        "user_id": str(user_id),
        "session_id": session_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")

def decode_token(token, verify_exp=True):
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"], options={"verify_exp": verify_exp})
    except jwt.ExpiredSignatureError:
        return None if verify_exp else jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"], options={"verify_exp": False})
    except jwt.InvalidTokenError:
        return None
    

def verify_jwt_token(token):
    """Decode the JWT token and return the user_id if valid."""
    try:
        decoded_token = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return decoded_token.get("user_id")  # Ensure this key exists in the token payload
    except jwt.ExpiredSignatureError:
        print("Token has expired")
        return None
    except jwt.InvalidTokenError:
        print("Invalid token")
        return None