from api.recovery_routes import router as recovery_router
from api.workout_routes import router as workout_router
from api.sleep_routes import router as sleep_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- for dev, allow everything
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(recovery_router)
app.include_router(workout_router)
app.include_router(sleep_router)
