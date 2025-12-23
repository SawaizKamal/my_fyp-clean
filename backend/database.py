import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ---------------- CONFIGURATION ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Check for Render's DATABASE_URL (for Postgres) or fallback to local SQLite
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    # Fix Render's postgres:// to postgresql:// for SQLAlchemy
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    # Local SQLite
    DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'users.db')}"

# ---------------- SETUP ----------------
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------- MODELS ----------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ---------------- HELPERS ----------------
def init_db():
    """Creates the tables if they don't exist."""
    print(f"Initializing database at {DATABASE_URL}")
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for FastAPI routes to get a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------- ACCESSORS (Legacy Support) ----------------
# NOTE: These are helper functions to maintain compatibility with existing auth.py
# Ideally, you should inject the 'db' session directly into routes/auth functions.

def get_user_by_username(username: str):
    db: Session = SessionLocal()
    try:
        return db.query(User).filter(User.username == username).first()
    finally:
        db.close()

def get_user_by_id(user_id: int):
    db: Session = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id).first()
    finally:
        db.close()

def create_user(username: str, email: str, hashed_password: str):
    db: Session = SessionLocal()
    try:
        new_user = User(username=username, email=email, hashed_password=hashed_password)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user.id
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
