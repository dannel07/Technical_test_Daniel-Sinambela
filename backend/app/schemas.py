from datetime import date
from typing import Optional
from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    name: str
    email: str


class UserOut(UserBase):
    id: int

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "Todo"
    deadline: date
    assignee_id: Optional[int] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(TaskBase):
    pass


class TaskStatusUpdate(BaseModel):
    status: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class TaskOut(TaskBase):
    id: int
    assignee: Optional[UserOut] = None

    class Config:
        from_attributes = True
