import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from openai import OpenAI
from sqlalchemy.orm import Session

from .ai_service import build_task_context, should_use_llm

load_dotenv()


def _normalize_status(status: str | None) -> str:
    return (status or "").strip().lower()


def _is_done_task(task) -> bool:
    return _normalize_status(getattr(task, "status", "")) in {"done", "selesai", "completed", "complete"}


def _parse_deadline(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except ValueError:
                return None
    return None


def _extract_task_title(message: str) -> str | None:
    normalized = message.strip().lower()
    for prefix in ["task ", "tugas ", "tasknya ", "tugasnya "]:
        if prefix in normalized:
            title = message[message.lower().find(prefix) + len(prefix) :].strip().rstrip("?").strip()
            if title:
                return title

    match = re.search(r"(?:task|tugas)\s+(.+)$", message, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip().rstrip("?")
    return None


def build_ai_reply(tasks, message: str) -> str:
    normalized = message.strip().lower()
    pending_tasks = [task for task in tasks if not _is_done_task(task)]
    completed_tasks = [task for task in tasks if _is_done_task(task)]

    def _find_task(title: str | None):
        if not title:
            return None
        title_lower = title.lower()
        return next((task for task in tasks if title_lower in getattr(task, "title", "").lower()), None)

    title = _extract_task_title(message)

    if "belum selesai" in normalized or "incomplete" in normalized or "todo" in normalized:
        if not pending_tasks:
            return "Tidak ada task yang belum selesai."
        lines = ["Berikut task yang belum selesai:"]
        for task in pending_tasks:
            assignee = getattr(getattr(task, "assignee", None), "name", "Unassigned")
            lines.append(f"- {task.title} | status: {task.status} | deadline: {task.deadline} | assignee: {assignee}")
        return "\n".join(lines)

    if "selesai" in normalized or "done" in normalized:
        if "jumlah" in normalized or "count" in normalized:
            return f"Jumlah task yang sudah selesai: {len(completed_tasks)} dari total {len(tasks)}."
        if not completed_tasks:
            return "Belum ada task yang selesai."
        lines = ["Berikut task yang sudah selesai:"]
        for task in completed_tasks:
            assignee = getattr(getattr(task, "assignee", None), "name", "Unassigned")
            lines.append(f"- {task.title} | assignee: {assignee}")
        return "\n".join(lines)

    if "deadline" in normalized and ("hari ini" in normalized or "today" in normalized):
        today = date.today()
        due_today = [task for task in tasks if _parse_deadline(getattr(task, "deadline", None)) == today]
        if not due_today:
            return "Tidak ada task dengan deadline hari ini."
        lines = ["Task yang deadlinenya hari ini:"]
        for task in due_today:
            assignee = getattr(getattr(task, "assignee", None), "name", "Unassigned")
            lines.append(f"- {task.title} | status: {task.status} | assignee: {assignee}")
        return "\n".join(lines)

    if "status" in normalized or "state" in normalized:
        if title:
            matched = _find_task(title)
            if matched:
                return f"Status task '{matched.title}' adalah {matched.status}."
        return "Saya tidak menemukan task dengan judul tersebut."

    if "assignee" in normalized or "penganggung jawab" in normalized or "owner" in normalized:
        if title:
            matched = _find_task(title)
            if matched:
                assignee = getattr(getattr(matched, "assignee", None), "name", "Unassigned")
                return f"Assignee dari task '{matched.title}' adalah {assignee}."
        return "Saya tidak menemukan task dengan judul tersebut."

    if "deskripsi" in normalized or "description" in normalized:
        if title:
            matched = _find_task(title)
            if matched:
                description = getattr(matched, "description", "") or "Tidak ada deskripsi."
                return f"Deskripsi dari task '{matched.title}' adalah: {description}"
        return "Saya tidak menemukan task dengan judul tersebut."

    if "deadline" in normalized or "due" in normalized:
        if title:
            matched = _find_task(title)
            if matched:
                return f"Deadline task '{matched.title}' adalah {matched.deadline}."
        return "Saya tidak menemukan task dengan judul tersebut."

    if "ringkasan" in normalized or "summary" in normalized or "overview" in normalized:
        lines = [f"Total task: {len(tasks)}", f"Belum selesai: {len(pending_tasks)}", f"Sudah selesai: {len(completed_tasks)}"]
        return "\n".join(lines)

    if "jumlah" in normalized or "count" in normalized:
        return f"Total task: {len(tasks)}. Belum selesai: {len(pending_tasks)}. Sudah selesai: {len(completed_tasks)}."

    if "daftar" in normalized or "list" in normalized or "semua task" in normalized:
        lines = ["Berikut daftar task:"]
        for task in tasks:
            assignee = getattr(getattr(task, "assignee", None), "name", "Unassigned")
            lines.append(f"- {task.title} | status: {task.status} | deadline: {task.deadline} | assignee: {assignee}")
        return "\n".join(lines)

    return "Saya bisa membantu melihat daftar task, status, deadline, assignee, deskripsi, dan ringkasan. Coba tanyakan seperti: 'Tampilkan semua task yang belum selesai', 'Apa status task Design review?', atau 'Siapa assignee dari task Design review?'"


def _is_task_related_query(message: str) -> bool:
    normalized = (message or "").strip().lower()
    keywords = [
        "task",
        "tugas",
        "deadline",
        "assignee",
        "owner",
        "status",
        "deskripsi",
        "description",
        "ringkasan",
        "summary",
        "todo",
        "done",
        "selesai",
        "belum selesai",
        "list",
        "daftar",
        "count",
        "jumlah",
    ]
    return any(keyword in normalized for keyword in keywords)


def _is_generic_llm_reply(reply: str | None) -> bool:
    if not reply:
        return True
    normalized = reply.strip().lower()
    generic_phrases = [
        "saya tidak memiliki informasi",
        "saya tidak bisa membantu",
        "saya tidak tahu",
        "i don't have",
        "i don't know",
        "i can't",
        "tidak ada informasi",
        "maaf, saya",
        "saya bisa membantu melihat daftar task",
    ]
    return any(phrase in normalized for phrase in generic_phrases)


def choose_best_reply(message: str, fallback_reply: str, llm_reply: str | None) -> str:
    if not llm_reply:
        return fallback_reply
    if _is_task_related_query(message) and _is_generic_llm_reply(llm_reply):
        return fallback_reply
    return llm_reply


def get_llm_reply(task_context: str, message: str, client=None) -> tuple[str | None, str | None]:
    if client is None and os.getenv("LLM_ENABLED", "false").lower() != "true":
        return None, "disabled"

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    if client is None and not api_key and base_url == "https://api.openai.com/v1":
        return None, "missing_api_key"

    try:
        runtime_client = client or OpenAI(api_key=api_key or "dummy", base_url=base_url)
        completion = runtime_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": f"You are a concise assistant for a task management app. Answer in Indonesian. Use this task data when relevant:\n{task_context}",
                },
                {"role": "user", "content": message},
            ],
            temperature=temperature,
        )
        reply = completion.choices[0].message.content.strip() if completion.choices else "Saya tidak bisa menghasilkan respons saat ini."
        return reply, None
    except Exception as exc:
        return None, str(exc)

from .database import Base, SessionLocal, engine, get_db
from .models import Task, User
from .schemas import ChatRequest, ChatResponse, LoginRequest, TaskCreate, TaskOut, TaskStatusUpdate, TaskUpdate, TokenResponse, UserOut

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
security = HTTPBearer(auto_error=False)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Management API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def seed_demo_user(db: Session) -> None:
    if db.query(User).filter(User.username == "admin").first():
        return

    demo_user = User(
        username="admin",
        name="Administrator",
        email="admin@example.com",
        password_hash="hashed-password",
    )
    db.add(demo_user)
    db.commit()


@app.on_event("startup")
def startup_event() -> None:
    db = SessionLocal()
    try:
        seed_demo_user(db)
    finally:
        db.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}



def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)] = None,
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    if credentials is None:
        raise credentials_exception

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or request.password != "password123":
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=token, token_type="bearer", user=UserOut.model_validate(user))


@app.get("/users", response_model=list[UserOut])
def get_users(
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    return db.query(User).all()


@app.get("/tasks", response_model=list[TaskOut])
def get_tasks(
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    return db.query(Task).join(User, Task.assignee_id == User.id, isouter=True).all()


@app.post("/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    db_task = Task(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return TaskOut.model_validate(db_task)


@app.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskOut.model_validate(task)


@app.put("/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    task: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    for key, value in task.model_dump().items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return TaskOut.model_validate(db_task)


@app.patch("/tasks/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db_task.status = payload.status
    db.commit()
    db.refresh(db_task)
    return TaskOut.model_validate(db_task)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] = None,
):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(db_task)
    db.commit()
    return None


@app.post("/ai/chat", response_model=ChatResponse)
def ai_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    fallback_reply = build_ai_reply(tasks, payload.message)
    if not should_use_llm(tasks, payload.message):
        return ChatResponse(reply=fallback_reply)

    task_context = build_task_context(tasks, payload.message)
    reply, error = get_llm_reply(task_context, payload.message)
    final_reply = choose_best_reply(payload.message, fallback_reply, reply)
    return ChatResponse(reply=final_reply)
