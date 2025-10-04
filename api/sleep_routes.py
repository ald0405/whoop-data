from db.database import get_db
from crud.sleep import get_sleep
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from schemas.sleep import SleepSchema

router = APIRouter()

@router.get("/sleep/",
            name="Get all sleeps",
            description="An endpoint for getting all sleep data",
            response_model=List[SleepSchema]
            )

def list_sleep(skip:int=0,limit:int=100,db:Session=Depends(get_db)):
    return get_sleep(db,skip=skip,limit=limit)
