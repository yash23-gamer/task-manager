from bson import ObjectId
from app import mongo
from app.utils.exceptions import CustomException
from app.utils.validators import validate_task_data
from typing import List, Dict, Optional
import uuid
from datetime import datetime, timedelta
import pytz
from flask import current_app
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import redis
from redis import Redis

# Initialize Redis cache
cache = Redis(host=current_app.config.get('REDIS_HOST', 'localhost'), port=6379, db=0)

class TaskService:
    """
    Service layer for task-related operations.
    
    Ensures all operations are scoped to the authenticated user and validates input data.
    """
    
    @classmethod
    def create_task(cls, user_id: str, title: str, description: str, status: str) -> str:
        """
        Creates a new task for a user.
        
        Args:
            user_id (str): ID of the task owner.
            title (str): Task title (min 3 characters).
            description (str): Task details (optional).
            status (str): Must be 'pending', 'in-progress', or 'completed'.
        
        Returns:
            str: The ID of the created task.
        
        Raises:
            CustomException: For invalid data or database errors.
        """
        if not validate_task_data(title, status):
            raise CustomException("Invalid task data", 400)
        
        # Start a transaction
        with mongo.db.client.start_session() as session:
            try:
                session.start_transaction()
                result = mongo.db.tasks.insert_one({
                    'title': title,
                    'description': description,
                    'status': status,
                    'user_id': user_id
                }, session=session)
                session.commit_transaction()
            except PyMongoError as e:
                session.abort_transaction()
                raise CustomException(f"Failed to create task: {str(e)}", 500)
        
        # Cache the task
        task_id = str(result.inserted_id)
        cls._cache_task(task_id, {
            'title': title,
            'description': description,
            'status': status,
            'user_id': user_id
        })
        
        return task_id

    @classmethod
    def get_user_tasks(cls, user_id: str, page: int = 1, limit: int = 20, 
                       sort_by: str = 'created_at', sort_order: str = 'desc',
                       status_filter: Optional[str] = None, title_filter: Optional[str] = None) -> (List[Dict], int):
        """
        Retrieves tasks for a user with pagination, sorting, and filtering.
        
        Args:
            user_id (str): ID of the task owner.
            page (int): Page number (default: 1).
            limit (int): Number of tasks per page (default: 20).
            sort_by (str): Field to sort by (default: 'created_at').
            sort_order (str): Sort order (default: 'desc').
            status_filter (str, optional): Filter tasks by status.
            title_filter (str, optional): Filter tasks by title.
        
        Returns:
            List[Dict]: Serialized tasks with pagination metadata.
            int: Total number of tasks.
        """
        # Build query
        query = {'user_id': user_id}
        if status_filter:
            query['status'] = status_filter
        if title_filter:
            query['title'] = {'$regex': title_filter, '$options': 'i'}
        
        # Get total count
        total = mongo.db.tasks.count_documents(query)
        
        # Apply sorting and pagination
        sort_direction = 1 if sort_order == 'asc' else -1
        tasks = list(mongo.db.tasks.find(query)
                     .sort(sort_by, sort_direction)
                     .skip((page - 1) * limit)
                     .limit(limit))
        
        # Cache tasks
        for task in tasks:
            cls._cache_task(str(task['_id']), {
                'title': task['title'],
                'description': task.get('description'),
                'status': task['status'],
                'user_id': task['user_id']
            })
        
        return [{'id': str(t['_id']), 'title': t['title'], 'description': t.get('description'), 'status': t['status']} for t in tasks], total

    @classmethod
    def get_task_by_id(cls, user_id: str, task_id: str) -> Optional[Dict]:
        """
        Retrieves a specific task by ID, verifying ownership.
        
        Args:
            user_id (str): ID of the task owner.
            task_id (str): MongoDB ObjectId as a string.
        
        Returns:
            Dict: Task details if found and owned by user.
        
        Raises:
            CustomException: If task not found or access denied.
        """
        # Try to get from cache first
        cached_task = cls._get_cached_task(task_id)
        if cached_task and cached_task.get('user_id') == user_id:
            return cached_task
        
        # Fetch from database
        try:
            task = mongo.db.tasks.find_one({
                '_id': ObjectId(task_id),
                'user_id': user_id
            })
        except Exception as e:
            raise CustomException(f"Invalid task ID format: {str(e)}", 400)
        
        if not task:
            raise CustomException("Task not found or access denied", 404)
        
        # Cache the task
        cls._cache_task(task_id, {
            'title': task['title'],
            'description': task.get('description'),
            'status': task['status'],
            'user_id': task['user_id']
        })
        
        return {
            'id': str(task['_id']),
            'title': task['title'],
            'description': task.get('description'),
            'status': task['status']
        }

    @classmethod
    def update_task(cls, user_id: str, task_id: str, updates: Dict) -> Dict:
        """
        Updates a task, enforcing ownership and valid status transitions.
        
        Args:
            user_id (str): ID of the task owner.
            task_id (str): MongoDB ObjectId as a string.
            updates (Dict): Fields to update (title, description, status).
        
        Returns:
            Dict: Updated task details.
        
        Raises:
            CustomException: For invalid data or access violations.
        """
        # Validate updates
        allowed_statuses = ['pending', 'in-progress', 'completed']
        if 'status' in updates and updates['status'] not in allowed_statuses:
            raise CustomException("Invalid status value", 400)
        
        # Start a transaction
        with mongo.db.client.start_session() as session:
            try:
                session.start_transaction()
                # Check task ownership
                task = mongo.db.tasks.find_one({'_id': ObjectId(task_id), 'user_id': user_id}, session=session)
                if not task:
                    session.abort_transaction()
                    raise CustomException("Task not found or access denied", 404)
                
                # Update task
                mongo.db.tasks.update_one(
                    {'_id': ObjectId(task_id), 'user_id': user_id},
                    {'$set': updates},
                    session=session
                )
                session.commit_transaction()
            except PyMongoError as e:
                session.abort_transaction()
                raise CustomException(f"Failed to update task: {str(e)}", 500)
        
        # Update cache
        task = cls.get_task_by_id(user_id, task_id)
        return task

    @classmethod
    def delete_task(cls, user_id: str, task_id: str) -> bool:
        """
        Deletes a task, verifying ownership.
        
        Args:
            user_id (str): ID of the task owner.
            task_id (str): MongoDB ObjectId as a string.
        
        Returns:
            bool: True if deleted, False otherwise.
        """
        # Start a transaction
        with mongo.db.client.start_session() as session:
            try:
                session.start_transaction()
                # Check task ownership and existence
                task = mongo.db.tasks.find_one({'_id': ObjectId(task_id), 'user_id': user_id}, session=session)
                if not task:
                    session.abort_transaction()
                    return False
                
                # Delete task
                result = mongo.db.tasks.delete_one({'_id': ObjectId(task_id), 'user_id': user_id}, session=session)
                session.commit_transaction()
            except PyMongoError as e:
                session.abort_transaction()
                raise CustomException(f"Failed to delete task: {str(e)}", 500)
        
        # Remove from cache
        cls._remove_cached_task(task_id)
        
        return result.deleted_count > 0

    @classmethod
    def _cache_task(cls, task_id: str, task_data: Dict) -> None:
        """Caches a task in Redis."""
        cache.set(f"task:{task_id}", json.dumps(task_data), ex=300)  # Cache for 5 minutes

    @classmethod
    def _get_cached_task(cls, task_id: str) -> Optional[Dict]:
        """Retrieves a cached task from Redis."""
        cached_data = cache.get(f"task:{task_id}")
        if cached_data:
            return json.loads(cached_data)
        return None

    @classmethod
    def _remove_cached_task(cls, task_id: str) -> None:
        """Removes a cached task from Redis."""
        cache.delete(f"task:{task_id}")