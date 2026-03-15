from fastapi import APIRouter, HTTPException

from whoopdata.clients.withings_client import WithingsClient
from whoopdata.database.database import SessionLocal
from whoopdata.models.models import WithingsHeartRate, WithingsWeight


data_router = APIRouter(prefix="/api/v1/data", tags=["data"])
legacy_data_router = APIRouter(tags=["data"])


@legacy_data_router.get("/auth/withings/status", deprecated=True)
@data_router.get("/integrations/withings/status")
async def withings_status():
    db = SessionLocal()

    try:
        client = WithingsClient()
        token_ok = False

        try:
            token_ok = client.validate_token()
        except Exception:
            token_ok = False

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

        return {
            "token_valid": token_ok,
            "latest_weight_datetime": (
                latest_weight.datetime.isoformat()
                if latest_weight and latest_weight.datetime
                else None
            ),
            "latest_heart_datetime": (
                latest_hr.datetime.isoformat() if latest_hr and latest_hr.datetime else None
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
