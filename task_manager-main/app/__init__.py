import logging
import os
import uuid
from flask import Flask, g, jsonify
from flask_jwt_extended import JWTManager
from flask_pymongo import PyMongo
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.config import get_config, Config
from app.utils.exceptions import CustomException
from dotenv import load_dotenv

# Initialize extensions
mongo = PyMongo()
jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
)
logger = logging.getLogger(__name__)

class RequestIDFilter(logging.Filter):
    """Logging filter to add request ID to log records."""
    def filter(self, record):
        record.request_id = getattr(g, 'request_id', 'no-request')
        return True

def create_app():
   
    # Create the Flask app
    app = Flask(__name__)

    # Load configuration based on environment
    app.config.from_object(get_config())

    # Load environment variables from .env file
    if not load_dotenv():
        logger.warning(".env file not found. Using environment variables directly.")

    # Check for required environment variables
    required_vars = ['DATABASE_URI', 'JWT_SECRET_KEY']
    missing_vars = [var for var in required_vars if not app.config.get(var)]
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise CustomException(error_msg, 500)

    # Initialize extensions
    mongo.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)

    # Configure logging with request ID
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s'
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestIDFilter())
    app.logger.handlers = []
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

    # Add request ID to each request
    @app.before_request
    def set_request_id():
        g.request_id = str(uuid.uuid4())

    # Global error handler
    @app.errorhandler(Exception)
    def handle_global_error(error):
        """Global error handler to return structured JSON responses."""
        if isinstance(error, CustomException):
            response = {
                'error': error.message,
                'status_code': error.status_code,
                'request_id': getattr(g, 'request_id', 'no-request')
            }
            return jsonify(response), error.status_code

        # Log unhandled exceptions
        app.logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
        response = {
            'error': 'Internal Server Error',
            'status_code': 500,
            'request_id': getattr(g, 'request_id', 'no-request')
        }
        return jsonify(response), 500

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.tasks import tasks_bp
    app.register_blueprint(auth_bp, url_prefix='/api')
    app.register_blueprint(tasks_bp, url_prefix='/api')

    logger.info("Flask application initialized successfully")
    return app