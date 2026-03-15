from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


router = APIRouter(prefix="/dashboard", include_in_schema=False)
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def dashboard_home(request: Request):
    """Serve the interactive dashboard HTML page."""
    return templates.TemplateResponse("dashboard.html", {"request": request})
