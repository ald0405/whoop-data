from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates


router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="templates")


@router.get("/")
async def homepage(request: Request):
    """Homepage with dashboard overview"""
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/analytics")
async def analytics_page(request: Request):
    """Analytics and insights dashboard"""
    return templates.TemplateResponse("analytics.html", {"request": request})


@router.get("/report")
async def weekly_report_page(request: Request):
    """Weekly coaching report"""
    return templates.TemplateResponse("weekly_report.html", {"request": request})
