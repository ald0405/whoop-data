from whoopdata.api.recovery_routes import router as recovery_router
from whoopdata.api.workout_routes import router as workout_router
from whoopdata.api.sleep_routes import router as sleep_router
from whoopdata.api.withings_routes import router as withings_router
from whoopdata.api.weather_routes import router as weather_router
from whoopdata.api.transport_routes import router as transport_router
from whoopdata.api.dashboard_routes import router as dashboard_router
from whoopdata.api.analytics_routes import router as analytics_router
from whoopdata.api.tide_routes import router as tide_router
from whoopdata.__version__ import __version__
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path

app = FastAPI(
    title="WHOOP Health Data Platform",
    description="A comprehensive health data integration platform for WHOOP and Withings devices",
    version=__version__,
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


# Analytics dashboard route
@app.get("/analytics")
async def analytics_page(request: Request):
    """Analytics and insights dashboard"""
    return templates.TemplateResponse("analytics.html", {"request": request})


# Include API routers
app.include_router(recovery_router)
app.include_router(workout_router)
app.include_router(sleep_router)
app.include_router(withings_router)

# Lightweight auth/status endpoint for Withings
from whoopdata.clients.withings_client import WithingsClient
from whoopdata.database.database import SessionLocal
from whoopdata.models.models import WithingsWeight, WithingsHeartRate
from fastapi import HTTPException

@app.get("/auth/withings/status")
async def withings_status():
    try:
        client = WithingsClient()
        token_ok = False
        try:
            token_ok = client.validate_token()
        except Exception:
            token_ok = False

        db = SessionLocal()
        latest_weight = (
            db.query(WithingsWeight)
            .filter(WithingsWeight.datetime.isnot(None))
            .order_by(WithingsWeight.datetime.desc())
            .first()
        )
        latest_hr = (
            db.query(WithingsHeartRate)
            .filter(WithingsHeartRate.datetime.isnot(None))
            .order_by(WithingsHeartRate.datetime.desc())
            .first()
        )
        db.close()

        return {
            "token_valid": token_ok,
            "latest_weight_datetime": latest_weight.datetime.isoformat() if latest_weight and latest_weight.datetime else None,
            "latest_heart_datetime": latest_hr.datetime.isoformat() if latest_hr and latest_hr.datetime else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
app.include_router(weather_router)
app.include_router(transport_router)
app.include_router(dashboard_router)
app.include_router(analytics_router)
app.include_router(tide_router)
