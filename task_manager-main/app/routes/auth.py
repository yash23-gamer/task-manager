from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.models.user import User
from app.utils.exceptions import CustomException
from pydantic import BaseModel, ValidationError, validator
from typing import Optional
import re

# Initialize blueprint and rate limiter
auth_bp = Blueprint('auth', __name__)
limiter = Limiter(key_func=get_remote_address)

# Pydantic models for request validation
class RegisterRequest(BaseModel):
    username: str
    password: str

    @validator('username')
    def username_min_length(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v

    @validator('password')
    def password_complexity(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one number")
        return v

class LoginRequest(BaseModel):
    username: str
    password: str

    @validator('username')
    def username_min_length(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v

@auth_bp.route('/register', methods=['POST'])
@limiter.limit("5 per minute")  # Prevent registration abuse
def register():
    """User registration endpoint.
    
    Request Body:
        - username (str): Unique username (min 3 characters).
        - password (str): Plain text password (min 8 characters, must include uppercase, lowercase, and a number).
    
    Responses:
        201: User created successfully.
        400: Invalid input data.
        409: Username already exists.
    """
    try:
        data = RegisterRequest(**request.get_json())
    except ValidationError as e:
        raise CustomException(str(e), 400)

    try:
        User.create(data.username, data.password)
    except CustomException as e:
        raise e

    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("10 per minute")  # Protect against brute-force attacks
def login():
    """User login endpoint with JWT token generation.
    
    Request Body:
        - username (str): Registered username.
        - password (str): Correct password.
    
    Responses:
        200: JWT access token.
        400: Invalid input data.
        401: Invalid credentials.
    """
    try:
        data = LoginRequest(**request.get_json())
    except ValidationError as e:
        raise CustomException(str(e), 400)

    user = User.get_by_username(data.username)
    if not user or not user.check_password(data.password):
        raise CustomException("Invalid credentials", 401)

    access_token = create_access_token(identity=str(user.id))
    return jsonify(access_token=access_token), 200