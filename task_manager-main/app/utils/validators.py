from pydantic import BaseModel, ValidationError, validator
import re

class UserValidationModel(BaseModel):
    """Pydantic model for user validation."""
    username: str
    password: str
    email: Optional[str] = None

    @validator('username')
    def username_min_length(cls, v):
        """Validate username length."""
        if len(v.strip()) < 3:
            raise ValueError("Username must be at least 3 characters")
        return v

    @validator('password')
    def password_complexity(cls, v):
        """Validate password complexity."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one number")
        return v

    @validator('email')
    def email_format(cls, v):
        """Validate email format."""
        if v and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError("Invalid email format")
        return v

def validate_user_data(data: dict) -> bool:
    """
    Validates user data using Pydantic model.
    
    Args:
        data (dict): User data to validate.
    
    Returns:
        bool: True if valid, else False.
    """
    try:
        UserValidationModel(**data)
        return True
    except ValidationError as e:
        print(f"Validation error: {e}")
        return False

def validate_task_data(title: str, status: str) -> bool:
    """
    Validates task title and status against application rules.
    
    Args:
        title (str): Task title to validate.
        status (str): Task status to validate.
    
    Returns:
        bool: True if valid, else False.
    """
    allowed_statuses = {'pending', 'in-progress', 'completed'}
    if not title or len(title.strip()) < 3:
        return False
    if status not in allowed_statuses:
        return False
    return True