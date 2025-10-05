from whoop_data.api.recovery_routes import router as recovery_router
from whoop_data.api.workout_routes import router as workout_router
from whoop_data.api.sleep_routes import router as sleep_router
from whoop_data.api.withings_routes import router as withings_router
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(
    title="WHOOP Health Data Platform",
    description="A comprehensive health data integration platform for WHOOP and Withings devices",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- for dev, allow everything
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up templates and static files
templates = Jinja2Templates(directory="templates")

# Mount static files (for CSS, JS, images)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    # Directory doesn't exist yet, we'll create it
    pass

# Homepage route
@app.get("/")
async def homepage(request: Request):
    """Homepage with dashboard overview"""
    return templates.TemplateResponse("index.html", {"request": request})

# Include API routers
app.include_router(recovery_router)
app.include_router(workout_router)
app.include_router(sleep_router)
app.include_router(withings_router)
