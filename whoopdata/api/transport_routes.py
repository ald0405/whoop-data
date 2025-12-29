"""Transport status API routes for TfL (Transport for London)."""

from fastapi import APIRouter, HTTPException
from whoopdata.services.transport_service import TravelAPI

router = APIRouter(prefix="/transport", tags=["transport"])

# Initialize transport service
transport_service = TravelAPI()


@router.get("/status")
async def get_transport_status():
    """Get current status of key TfL lines.

    Returns status for lines relevant to South Quay DLR area:
    - Jubilee Line
    - DLR (Docklands Light Railway)
    - Elizabeth Line
    - Northern Line

    Returns:
        Dict mapping line names to their status and description.
        Status is either "Good Service" or describes the disruption.
    """
    try:
        line_status = transport_service.get_line_status()

        return {"lines": line_status, "total_lines": len(line_status), "timestamp": "now"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch transport status: {str(e)}")


@router.get("/arrivals")
async def get_train_arrivals(limit: int = 5):
    """Get real-time train arrivals for key stations.

    Fetches arrivals from:
    - DLR South Quay Station
    - Jubilee Line Canary Wharf Underground
    - Elizabeth Line Canary Wharf

    Returns the next trains sorted by arrival time.

    Args:
        limit: Maximum number of arrivals to return (default: 5)

    Returns:
        Dict with arrivals list containing line, destination, platform, and time.
    """
    try:
        arrivals_data = transport_service.get_station_arrivals(limit=limit)
        return arrivals_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch train arrivals: {str(e)}")
