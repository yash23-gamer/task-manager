```markdown
# Task Manager API
**RESTful API for managing tasks with JWT authentication**

[![Deployed on Render](https://img.shields.io/badge/Deployed%20on-Render-blue)](https://your-render-url.com)

---

## Project Overview
A backend-only task management API built with:
- **Python 3.10** + **Flask**
- **MongoDB** (via Flask-PyMongo)
- **JWT Authentication** (Flask-JWT-Extended)
- Rate limiting and input validation

**Features**:
- User registration/login with secure password hashing
- CRUD operations for tasks (scoped to authenticated users)
- RESTful endpoints with proper HTTP status codes

---

## Local Setup & Execution

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/task-manager-api.git
cd task-manager-api
```

### 2. Set up environment
```bash
pipenv install   # Install dependencies from Pipfile
pipenv shell     # Activate virtual environment
```

### 3. Configure environment variables
Create a `.env` file with:
```ini
DATABASE_URI=mongodb://localhost:27017/taskmanager
JWT_SECRET_KEY=your-secret-key
FLASK_ENV=development
```

### 4. Run the application
```bash
flask run  # Starts server at http://localhost:5000
```

---

## Deployed API
**Base URL**:  
`https://your-render-url.com/api`

---

## Postman Collection
**Collection Link**:  
[![Run in Postman](https://run.pstmn.io/button.svg)](https://www.postman.com/collection/xyz123)

**Import Instructions**:
1. Download the [Postman Collection JSON](./postman_collection.json).
2. Import into Postman via **File > Import**.
3. Use the "Login" request to generate a JWT token.
4. Token auto-populates in other requests via `{{JWT_TOKEN}}` variable.

---

## API Endpoints
*(All task endpoints require `Authorization: Bearer <JWT>` header)*

### Authentication
#### **Register**  
- **POST** `/api/register`  
- **Body**:
  ```json
  { "username": "user1", "password": "Pass1234!" }
  ```
- **Response**: `201 Created`

#### **Login**  
- **POST** `/api/login`  
- **Body**:
  ```json
  { "username": "user1", "password": "Pass1234!" }
  ```
- **Response**:
  ```json
  { "access_token": "jwt-token-here" }
  ```

### Tasks (Protected)
#### **Create Task**  
- **POST** `/api/tasks`  
- **Body**:
  ```json
  {
    "title": "Buy groceries",
    "description": "Milk, Bread",
    "status": "pending"
  }
  ```
- **Response**:
  ```json
  { "id": "abc123", "message": "Task created" }
  ```

#### **List Tasks**  
- **GET** `/api/tasks`  
- **Headers**: `Authorization: Bearer {{JWT_TOKEN}}`  
- **Response**:
  ```json
  [
    {
      "id": "abc123",
      "title": "Buy groceries",
      "status": "pending"
    }
  ]
  ```

#### **Get Task Details**  
- **GET** `/api/tasks/<task_id>`  
- **Example**: `/api/tasks/abc123`

#### **Update Task**  
- **PATCH** `/api/tasks/<task_id>`  
- **Body**: `{ "status": "completed" }`

#### **Delete Task**  
- **DELETE** `/api/tasks/<task_id>`

---

## Deployment (Render)
### Render Setup
1. Link GitHub repository to Render.
2. Set environment variables:
   ```ini
   DATABASE_URI=mongodb+srv://<user>:<password>@cluster0.mongodb.net/taskmanager
   JWT_SECRET_KEY=production-secret-key
   FLASK_ENV=production
   ```

### Database
- Uses MongoDB Atlas cluster (free tier).

---

## Directory Structure
```
task-manager-api/
├── app/
│   ├── __init__.py
│   ├── models/
│   │   ├── user.py
│   │   └── task.py
│   ├── routes/
│   │   ├── auth.py
│   │   └── tasks.py
│   └── ...
├── .env
├── Pipfile
└── README.md
```

---

**License**: MIT  
**Contributors**: rajbhoyar729
``` 

---