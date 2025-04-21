from api.recovery_routes import router as recovery_router
from api.workout_routes import router as workout_router
from fastapi import FastAPI 

app = FastAPI()
app.include_router(recovery_router)
app.include_router(workout_router)
