# Task Management App

A simple task management application with React (Next.js) frontend and FastAPI backend. It supports task CRUD, JWT-based login, assignee assignment, PostgreSQL persistence, and an AI chatbot for task-related questions.

## Features
- Login with a hardcoded demo user
- View all tasks
- Create, edit, and delete tasks
- Change task status
- Assign tasks to users from a user list
- Store data in PostgreSQL
- AI chatbot endpoint for task questions

## Tech Stack
- Frontend: Next.js, React
- Backend: FastAPI
- Database: PostgreSQL via SQLAlchemy
- AI: OpenAI-compatible model with local fallback logic

## Prerequisites
- Python 3.10+
- Node.js 18+
- Docker Desktop (for PostgreSQL)

## Run Database
```bash
cd D:\Moonlay_Test
docker compose up -d db
```

## Run Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
set PYTHONPATH=D:\Moonlay_Test\backend
set LLM_ENABLED=true
set OPENAI_API_KEY=your-openai-key
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010
```

## Run Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Overview
- POST /auth/login
- GET /users
- GET /tasks
- POST /tasks
- PUT /tasks/{task_id}
- PATCH /tasks/{task_id}/status
- DELETE /tasks/{task_id}
- POST /ai/chat

## Demo Login
- Username: admin
- Password: password123

## AI Chatbot
The chatbot uses a rule-based fallback first to keep token usage low, and only calls the LLM when the question is more open-ended. It can answer questions such as:
- Show all incomplete tasks
- Count completed tasks
- List tasks due today
- Identify the assignee of a task

## Verification
Verified locally:
- Backend tests: 9/9 passed
- Frontend build: successful
- PostgreSQL container: running

## Postman
Import [docs/postman_collection.json](docs/postman_collection.json) into Postman.

## ERD
The entity relationship diagram is available in [docs/erd.png](docs/erd.png).
