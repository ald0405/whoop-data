from sqlalchemy import create_engine
from models.models import (
    Base,
    Cycle,
    Sleep,
    Recovery,
    Workout,
)  # make sure all models are here
import os

DB_PATH = "db/whoop.db"

# Ensure db folder exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# If file exists but is not writable, fix permissions
if os.path.exists(DB_PATH) and not os.access(DB_PATH, os.W_OK):
    print(f"⚠️  {DB_PATH} is not writable. Attempting to fix permissions...")
    os.chmod(DB_PATH, 0o664)  # Add write permission for user/group

engine = create_engine("sqlite:///db/whoop.db")

print("Creating tables for:", Base.metadata.tables.keys())  # 🔍 check registration
Base.metadata.create_all(bind=engine)
print("✅ Tables created")
