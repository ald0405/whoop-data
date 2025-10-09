from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Path to your SQLite database file
DATABASE_URL = "sqlite:///whoopdata/database/whoop.db"

# Create the SQLAlchemy engine
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
def get_db():
    """
    Dependency function to get a database session.
    Yields a session and ensures it's closed after the request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
Usage:
from whoopdata.database.database import SessionLocal, engine

# To create a session:
db = SessionLocal()

# Don't forget to close it:
db.close()

Used by FastAPI dependency injection like:
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""
