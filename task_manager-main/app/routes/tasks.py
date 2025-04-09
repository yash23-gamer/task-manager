from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.task_service import TaskService
from app.utils.exceptions import CustomException
from app.utils.validators import validate_task_data
from pydantic import BaseModel, ValidationError, validator
from typing import Dict, Optional, List

tasks_bp = Blueprint('tasks', __name__)

# Pydantic model for task creation
class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    status: str

    @validator('title')
    def title_min_length(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Title must be at least 3 characters")
        return v

    @validator('status')
    def status_must_be_valid(cls, v):
        allowed_statuses = ['pending', 'in-progress', 'completed']
        if v not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}")
        return v

# Pydantic model for task update
class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

    @validator('title')
    def title_min_length(cls, v):
        if v and len(v.strip()) < 3:
            raise ValueError("Title must be at least 3 characters")
        return v

    @validator('status')
    def status_must_be_valid(cls, v):
        allowed_statuses = ['pending', 'in-progress', 'completed']
        if v and v not in allowed_statuses:
            raise ValueError(f"Status must be one of {allowed_statuses}")
        return v

@tasks_bp.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    """Create a new task for the authenticated user.
    
    Request Body:
        - title (str): Task title (required, min 3 characters).
        - description (str, optional): Task details.
        - status (str, optional): Must be 'pending', 'in-progress', or 'completed'.
    
    Responses:
        201: Task created successfully.
        400: Invalid input data.
    """
    try:
        data = TaskCreateRequest(**request.get_json())
    except ValidationError as e:
        raise CustomException(str(e), 400)

    user_id = get_jwt_identity()
    task_id, error = TaskService.create_task(
        user_id=user_id,
        title=data.title,
        description=data.description,
        status=data.status
    )
    if error:
        raise CustomException(error, 400)

    return jsonify({'id': task_id, 'message': 'Task created'}), 201

@tasks_bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    """Retrieve tasks for the authenticated user with pagination, sorting, and filtering.
    
    Query Parameters:
        - page (int, optional): Page number (default: 1).
        - limit (int, optional): Number of tasks per page (default: 20).
        - sort_by (str, optional): Field to sort by (title, status, created_at).
        - sort_order (str, optional): Sort order (asc, desc).
        - status (str, optional): Filter tasks by status.
        - title (str, optional): Filter tasks by title.
    
    Responses:
        200: List of tasks.
    """
    user_id = get_jwt_identity()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 20))
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    status_filter = request.args.get('status')
    title_filter = request.args.get('title')

    tasks, total = TaskService.get_user_tasks(
        user_id=user_id,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        status_filter=status_filter,
        title_filter=title_filter
    )
    return jsonify({
        'tasks': tasks,
        'total': total,
        'page': page,
        'limit': limit
    }), 200

@tasks_bp.route('/tasks/<task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    """Retrieve a specific task by ID.
    
    Responses:
        200: Task details.
        404: Task not found or access denied.
    """
    user_id = get_jwt_identity()
    task = TaskService.get_task_by_id(user_id, task_id)
    if not task:
        raise CustomException("Task not found", 404)
    return jsonify(task), 200

@tasks_bp.route('/tasks/<task_id>', methods=['PUT'])
@jwt_required()
def update_task_put(task_id):
    """Fully replace a task's data (all fields required).
    
    Request Body:
        - title (str): New title.
        - description (str): New description.
        - status (str): New status.
    
    Responses:
        200: Updated task details.
        400: Invalid data.
        404: Task not found.
    """
    try:
        data = TaskCreateRequest(**request.get_json())
    except ValidationError as e:
        raise CustomException(str(e), 400)

    user_id = get_jwt_identity()
    task, error = TaskService.update_task(user_id, task_id, data.dict())
    if error:
        raise CustomException(error, 400)
    return jsonify(task), 200

@tasks_bp.route('/tasks/<task_id>', methods=['PATCH'])
@jwt_required()
def update_task_patch(task_id):
    """Partially update a task's data.
    
    Request Body:
        - title (str, optional)
        - description (str, optional)
        - status (str, optional)
    
    Responses:
        200: Updated task details.
        400: Invalid data.
        404: Task not found.
    """
    try:
        data = TaskUpdateRequest(**request.get_json())
    except ValidationError as e:
        raise CustomException(str(e), 400)

    user_id = get_jwt_identity()
    task, error = TaskService.update_task(user_id, task_id, data.dict(exclude_unset=True))
    if error:
        raise CustomException(error, 400)
    return jsonify(task), 200

@tasks_bp.route('/tasks/<task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """Delete a task by ID.
    
    Responses:
        200: Task deleted.
        404: Task not found.
    """
    user_id = get_jwt_identity()
    success = TaskService.delete_task(user_id, task_id)
    if not success:
        raise CustomException("Task not found", 404)
    return jsonify({'message': 'Task deleted'}), 200