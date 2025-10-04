from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, schemas, crud
from typing import List

from db.database import SessionLocal, engine

app = FastAPI()
# create tables if you haven’t already

models.Base.metadata.create_all(bind=engine)
# dependency: get a DB session, close after request


def get_db():
    """
    Making connection to Whoop DB and closes after each request
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/recoveries/", response_model=List[schemas.Recovery])
def list_recoveries(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_recoveries(db, skip=skip, limit=limit)
