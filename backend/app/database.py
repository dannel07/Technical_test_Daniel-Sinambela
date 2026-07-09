import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import ArgumentError
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
if not DATABASE_URL or DATABASE_URL.lower() in {"none", "null"} or DATABASE_URL.startswith("your-"):
    DATABASE_URL = "sqlite:///./task_app.db"

try:
    if DATABASE_URL.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        engine = create_engine(DATABASE_URL, connect_args=connect_args)
    else:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
except ArgumentError:
    DATABASE_URL = "sqlite:///./task_app.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
