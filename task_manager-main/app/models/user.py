from werkzeug.security import generate_password_hash, check_password_hash
from app import mongo
from app.utils.exceptions import CustomException
from bson import ObjectId
import re
from typing import Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import pytz

class User:
    """
    User model representing a user in the system.
    
    Attributes:
        username (str): Unique identifier for the user.
        password_hash (str): Hashed password (plain text passwords are never stored).
        id (ObjectId, optional): MongoDB document ID (automatically generated).
    """
    
    def __init__(self, username: str, password_hash: str, id: Optional[ObjectId] = None):
        self.username = username
        self.password_hash = password_hash
        self.id = id

    @classmethod
    def create(cls, username: str, password: str) -> 'User':
        """
        Creates a new user with secure password hashing.
        
        Args:
            username (str): Desired username (must be unique).
            password (str): Plain text password.
        
        Returns:
            User: The created user instance.
        
        Raises:
            CustomException: If username already exists or validation fails.
        """
        # Validate input
        if not cls._validate_username(username):
            raise CustomException("Username must be at least 3 characters", 400)
        if not cls._validate_password(password):
            raise CustomException("Password must be at least 8 characters and include uppercase, lowercase, and a number", 400)
        
        # Check for existing user
        existing_user = mongo.db.users.find_one({'username': username})
        if existing_user:
            raise CustomException("Username already exists", 409)
        
        # Hash password and insert into MongoDB
        password_hash = generate_password_hash(password)
        result = mongo.db.users.insert_one({
            'username': username,
            'password_hash': password_hash
        })
        return cls(username, password_hash, id=result.inserted_id)

    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        """
        Retrieves a user by their username.
        
        Args:
            username (str): The username to search for.
        
        Returns:
            User: The user instance if found, else None.
        """
        user_data = mongo.db.users.find_one({'username': username})
        return cls(**user_data) if user_data else None

    @classmethod
    def get_by_id(cls, user_id: ObjectId) -> Optional['User']:
        """
        Retrieves a user by their MongoDB ObjectId.
        
        Args:
            user_id (ObjectId): The user's unique database ID.
        
        Returns:
            User: The user instance if found, else None.
        """
        user_data = mongo.db.users.find_one({'_id': user_id})
        return cls(**user_data) if user_data else None

    def check_password(self, password: str) -> bool:
        """
        Verifies a plain text password against the stored hash.
        
        Args:
            password (str): The password to check.
        
        Returns:
            bool: True if password matches, else False.
        """
        return check_password_hash(self.password_hash, password)

    def update_password(self, new_password: str) -> None:
        """
        Updates the user's password with a new secure hash.
        
        Args:
            new_password (str): New plain text password.
        
        Raises:
            CustomException: If password validation fails.
        """
        if not self._validate_password(new_password):
            raise CustomException("Password must be at least 8 characters and include uppercase, lowercase, and a number", 400)
        new_hash = generate_password_hash(new_password)
        mongo.db.users.update_one(
            {'_id': self.id},
            {'$set': {'password_hash': new_hash}}
        )
        self.password_hash = new_hash

    def generate_password_reset_token(self, expires_in: int = 3600) -> str:
        """
        Generates a password reset token for the user.
        
        Args:
            expires_in (int): Number of seconds until the token expires (default: 3600).
        
        Returns:
            str: The password reset token.
        """
        token = str(uuid.uuid4())
        mongo.db.users.update_one(
            {'_id': self.id},
            {'$set': {
                'reset_token': token,
                'reset_token_expiry': datetime.now(pytz.utc) + timedelta(seconds=expires_in)
            }}
        )
        return token

    @classmethod
    def reset_password(cls, token: str, new_password: str) -> bool:
        """
        Resets the user's password using a valid reset token.
        
        Args:
            token (str): The password reset token.
            new_password (str): The new password to set.
        
        Returns:
            bool: True if password was reset successfully, else False.
        """
        user_data = mongo.db.users.find_one({
            'reset_token': token,
            'reset_token_expiry': {'$gt': datetime.now(pytz.utc)}
        })
        if not user_data:
            return False
        
        user = cls(**user_data)
        user.update_password(new_password)
        mongo.db.users.update_one(
            {'_id': user.id},
            {'$unset': {'reset_token': "", 'reset_token_expiry': ""}}
        )
        return True

    @staticmethod
    def _validate_username(username: str) -> bool:
        """
        Validates that the username meets the minimum length requirement.
        
        Args:
            username (str): The username to validate.
        
        Returns:
            bool: True if valid, else False.
        """
        return username and len(username.strip()) >= 3

    @staticmethod
    def _validate_password(password: str) -> bool:
        """
        Validates that the password meets complexity requirements.
        
        Args:
            password (str): The password to validate.
        
        Returns:
            bool: True if valid, else False.
        
        Rules:
            - Password must be at least 8 characters long.
            - Must contain at least one uppercase letter.
            - Must contain at least one lowercase letter.
            - Must contain at least one digit.
        """
        if len(password) < 8:
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[a-z]', password):
            return False
        if not re.search(r'\d', password):
            return False
        return True