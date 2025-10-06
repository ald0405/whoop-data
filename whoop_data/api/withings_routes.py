from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.database import get_db
from whoop_data.models.models import WithingsWeight, WithingsHeartRate
from typing import List, Optional, Union
from datetime import datetime, timedelta
import pandas as pd

router = APIRouter()

@router.get("/withings/weight", response_model=Union[List[dict], dict])
async def get_weight_data(
    latest: bool = Query(False, description="Get only the latest record"),
    limit: int = Query(100, description="Maximum number of records to return"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user_id: str = Query("default_user", description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Unified Withings weight endpoint with flexible filtering.
    
    Examples:
    - GET /withings/weight - All weight data
    - GET /withings/weight?latest=true - Latest weight only
    - GET /withings/weight?start_date=2024-01-01&end_date=2024-12-31 - Year 2024 data
    - GET /withings/weight?limit=50&skip=100 - Pagination
    """
    try:
        query = db.query(WithingsWeight).filter(WithingsWeight.user_id == user_id)
        
        # Apply date filters if provided
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(WithingsWeight.datetime >= start_dt)
        
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(WithingsWeight.datetime <= end_dt)
        
        if latest:
            # Get only the latest record
            record = query.filter(WithingsWeight.weight_kg.isnot(None)).order_by(WithingsWeight.datetime.desc()).first()
            if not record:
                raise HTTPException(status_code=404, detail="No weight data found")
            
            return {
                "id": record.id,
                "user_id": record.user_id,
                "datetime": record.datetime.isoformat() if record.datetime else None,
                "weight_kg": record.weight_kg,
                "height_m": record.height_m,
                "fat_free_mass_kg": record.fat_free_mass_kg,
                "fat_ratio_percent": record.fat_ratio_percent,
                "fat_mass_kg": record.fat_mass_kg,
                "muscle_mass_kg": record.muscle_mass_kg,
                "bone_mass_kg": record.bone_mass_kg,
                "hydration_kg": record.hydration_kg,
                "visceral_fat": record.visceral_fat,
                "bmi": record.bmi(),
                "weight_category": record.weight_category(),
                "deviceid": record.deviceid,
                "timezone": record.timezone,
                "comment": record.comment
            }
        
        # Get multiple records with pagination
        records = query.order_by(WithingsWeight.datetime.desc()).offset(skip).limit(limit).all()
        
        # Convert to dict format
        result = []
        for record in records:
            data = {
                "id": record.id,
                "user_id": record.user_id,
                "datetime": record.datetime.isoformat() if record.datetime else None,
                "weight_kg": record.weight_kg,
                "height_m": record.height_m,
                "fat_free_mass_kg": record.fat_free_mass_kg,
                "fat_ratio_percent": record.fat_ratio_percent,
                "fat_mass_kg": record.fat_mass_kg,
                "muscle_mass_kg": record.muscle_mass_kg,
                "bone_mass_kg": record.bone_mass_kg,
                "hydration_kg": record.hydration_kg,
                "visceral_fat": record.visceral_fat,
                "bmi": record.bmi(),
                "weight_category": record.weight_category(),
                "deviceid": record.deviceid,
                "timezone": record.timezone,
                "comment": record.comment
            }
            result.append(data)
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving weight data: {str(e)}")


@router.get("/withings/weight/latest")
async def get_latest_weight(
    db: Session = Depends(get_db),
    user_id: str = Query("default_user", description="User ID")
):
    """
    Get the most recent weight measurement
    """
    try:
        record = db.query(WithingsWeight)\
                   .filter(WithingsWeight.user_id == user_id)\
                   .filter(WithingsWeight.weight_kg.isnot(None))\
                   .order_by(WithingsWeight.datetime.desc())\
                   .first()
        
        if not record:
            raise HTTPException(status_code=404, detail="No weight data found")
        
        return {
            "id": record.id,
            "user_id": record.user_id,
            "datetime": record.datetime.isoformat() if record.datetime else None,
            "weight_kg": record.weight_kg,
            "bmi": record.bmi(),
            "weight_category": record.weight_category(),
            "fat_ratio_percent": record.fat_ratio_percent,
            "fat_mass_kg": record.fat_mass_kg,
            "muscle_mass_kg": record.muscle_mass_kg
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest weight: {str(e)}")


@router.get("/withings/weight/analytics")
async def get_weight_stats(
    db: Session = Depends(get_db),
    user_id: str = Query("default_user", description="User ID"),
    days: int = Query(30, description="Number of days to analyze")
):
    """
    Get weight statistics over a specified period
    """
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        records = db.query(WithingsWeight)\
                   .filter(WithingsWeight.user_id == user_id)\
                   .filter(WithingsWeight.weight_kg.isnot(None))\
                   .filter(WithingsWeight.datetime >= start_date)\
                   .order_by(WithingsWeight.datetime.asc())\
                   .all()
        
        if not records:
            raise HTTPException(status_code=404, detail="No weight data found for the specified period")
        
        weights = [r.weight_kg for r in records]
        
        # Calculate statistics
        current_weight = weights[-1] if weights else None
        min_weight = min(weights) if weights else None
        max_weight = max(weights) if weights else None
        avg_weight = sum(weights) / len(weights) if weights else None
        weight_change = weights[-1] - weights[0] if len(weights) >= 2 else 0
        
        # Get latest BMI and category
        latest_record = records[-1]
        
        return {
            "period_days": days,
            "total_measurements": len(records),
            "current_weight_kg": current_weight,
            "min_weight_kg": min_weight,
            "max_weight_kg": max_weight,
            "avg_weight_kg": round(avg_weight, 1) if avg_weight else None,
            "weight_change_kg": round(weight_change, 1),
            "current_bmi": latest_record.bmi(),
            "weight_category": latest_record.weight_category(),
            "start_date": start_date.date().isoformat(),
            "end_date": datetime.now().date().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating weight stats: {str(e)}")


@router.get("/withings/heart-rate", response_model=Union[List[dict], dict])
async def get_heart_rate_data(
    latest: bool = Query(False, description="Get only the latest record"),
    limit: int = Query(100, description="Maximum number of records to return"),
    skip: int = Query(0, description="Number of records to skip for pagination"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user_id: str = Query("default_user", description="User ID"),
    db: Session = Depends(get_db)
):
    """
    Unified Withings heart rate endpoint with flexible filtering.
    
    Examples:
    - GET /withings/heart-rate - All heart rate data
    - GET /withings/heart-rate?latest=true - Latest heart rate only
    - GET /withings/heart-rate?start_date=2024-01-01&end_date=2024-12-31 - Year 2024 data
    - GET /withings/heart-rate?limit=50&skip=100 - Pagination
    """
    try:
        query = db.query(WithingsHeartRate).filter(WithingsHeartRate.user_id == user_id)
        
        # Apply date filters if provided
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(WithingsHeartRate.datetime >= start_dt)
        
        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(WithingsHeartRate.datetime <= end_dt)
        
        if latest:
            # Get only the latest record
            record = query.order_by(WithingsHeartRate.datetime.desc()).first()
            if not record:
                raise HTTPException(status_code=404, detail="No heart rate data found")
            
            return {
                "id": record.id,
                "user_id": record.user_id,
                "datetime": record.datetime.isoformat() if record.datetime else None,
                "heart_rate_bpm": record.heart_rate_bpm,
                "systolic_bp_mmhg": record.systolic_bp_mmhg,
                "diastolic_bp_mmhg": record.diastolic_bp_mmhg,
                "bp_category": record.bp_category(),
                "deviceid": record.deviceid,
                "timezone": record.timezone
            }
        
        # Get multiple records with pagination
        records = query.order_by(WithingsHeartRate.datetime.desc()).offset(skip).limit(limit).all()
        
        # Convert to dict format
        result = []
        for record in records:
            data = {
                "id": record.id,
                "user_id": record.user_id,
                "datetime": record.datetime.isoformat() if record.datetime else None,
                "heart_rate_bpm": record.heart_rate_bpm,
                "systolic_bp_mmhg": record.systolic_bp_mmhg,
                "diastolic_bp_mmhg": record.diastolic_bp_mmhg,
                "bp_category": record.bp_category(),
                "deviceid": record.deviceid,
                "timezone": record.timezone
            }
            result.append(data)
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving heart rate data: {str(e)}")


@router.get("/withings/heart-rate/latest")
async def get_latest_heart_rate(
    db: Session = Depends(get_db),
    user_id: str = Query("default_user", description="User ID")
):
    """
    Get the most recent heart rate/blood pressure measurement
    """
    try:
        record = db.query(WithingsHeartRate)\
                   .filter(WithingsHeartRate.user_id == user_id)\
                   .order_by(WithingsHeartRate.datetime.desc())\
                   .first()
        
        if not record:
            raise HTTPException(status_code=404, detail="No heart rate data found")
        
        return {
            "id": record.id,
            "user_id": record.user_id,
            "datetime": record.datetime.isoformat() if record.datetime else None,
            "heart_rate_bpm": record.heart_rate_bpm,
            "systolic_bp_mmhg": record.systolic_bp_mmhg,
            "diastolic_bp_mmhg": record.diastolic_bp_mmhg,
            "bp_category": record.bp_category()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest heart rate: {str(e)}")


@router.get("/withings/summary")
async def get_withings_summary(
    db: Session = Depends(get_db),
    user_id: str = Query("default_user", description="User ID")
):
    """
    Get a summary of all Withings data
    """
    try:
        # Latest weight data
        latest_weight = db.query(WithingsWeight)\
                         .filter(WithingsWeight.user_id == user_id)\
                         .filter(WithingsWeight.weight_kg.isnot(None))\
                         .order_by(WithingsWeight.datetime.desc())\
                         .first()
        
        # Latest heart rate data  
        latest_hr = db.query(WithingsHeartRate)\
                     .filter(WithingsHeartRate.user_id == user_id)\
                     .order_by(WithingsHeartRate.datetime.desc())\
                     .first()
        
        # Count total records
        weight_count = db.query(WithingsWeight).filter(WithingsWeight.user_id == user_id).count()
        hr_count = db.query(WithingsHeartRate).filter(WithingsHeartRate.user_id == user_id).count()
        
        summary = {
            "user_id": user_id,
            "total_weight_records": weight_count,
            "total_heart_rate_records": hr_count,
            "latest_weight": None,
            "latest_heart_rate": None
        }
        
        if latest_weight:
            summary["latest_weight"] = {
                "datetime": latest_weight.datetime.isoformat() if latest_weight.datetime else None,
                "weight_kg": latest_weight.weight_kg,
                "bmi": latest_weight.bmi(),
                "weight_category": latest_weight.weight_category(),
                "fat_ratio_percent": latest_weight.fat_ratio_percent
            }
        
        if latest_hr:
            summary["latest_heart_rate"] = {
                "datetime": latest_hr.datetime.isoformat() if latest_hr.datetime else None,
                "heart_rate_bpm": latest_hr.heart_rate_bpm,
                "systolic_bp_mmhg": latest_hr.systolic_bp_mmhg,
                "diastolic_bp_mmhg": latest_hr.diastolic_bp_mmhg,
                "bp_category": latest_hr.bp_category()
            }
        
        return summary
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving Withings summary: {str(e)}")


# ============================================================================
# BACKWARD COMPATIBILITY ROUTES (for website)
# ============================================================================

@router.get("/withings/weight/latest")
async def get_latest_weight_compat(
    db: Session = Depends(get_db),
    user_id: str = Query("default_user", description="User ID")
):
    """Backward compatibility endpoint - redirects to unified weight endpoint."""
    try:
        record = db.query(WithingsWeight)\
                   .filter(WithingsWeight.user_id == user_id)\
                   .filter(WithingsWeight.weight_kg.isnot(None))\
                   .order_by(WithingsWeight.datetime.desc())\
                   .first()
        
        if not record:
            raise HTTPException(status_code=404, detail="No weight data found")
        
        return {
            "id": record.id,
            "user_id": record.user_id,
            "datetime": record.datetime.isoformat() if record.datetime else None,
            "weight_kg": record.weight_kg,
            "bmi": record.bmi(),
            "weight_category": record.weight_category(),
            "fat_ratio_percent": record.fat_ratio_percent,
            "fat_mass_kg": record.fat_mass_kg,
            "muscle_mass_kg": record.muscle_mass_kg
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest weight: {str(e)}")


@router.get("/withings/weight/stats")
async def get_weight_stats_compat(
    db: Session = Depends(get_db),
    user_id: str = Query("default_user", description="User ID"),
    days: int = Query(30, description="Number of days to analyze")
):
    """Backward compatibility endpoint - redirects to analytics endpoint."""
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        records = db.query(WithingsWeight)\
                   .filter(WithingsWeight.user_id == user_id)\
                   .filter(WithingsWeight.weight_kg.isnot(None))\
                   .filter(WithingsWeight.datetime >= start_date)\
                   .order_by(WithingsWeight.datetime.asc())\
                   .all()
        
        if not records:
            raise HTTPException(status_code=404, detail="No weight data found for the specified period")
        
        weights = [r.weight_kg for r in records]
        
        # Calculate statistics
        current_weight = weights[-1] if weights else None
        min_weight = min(weights) if weights else None
        max_weight = max(weights) if weights else None
        avg_weight = sum(weights) / len(weights) if weights else None
        weight_change = weights[-1] - weights[0] if len(weights) >= 2 else 0
        
        # Get latest BMI and category
        latest_record = records[-1]
        
        return {
            "period_days": days,
            "total_measurements": len(records),
            "current_weight_kg": current_weight,
            "min_weight_kg": min_weight,
            "max_weight_kg": max_weight,
            "avg_weight_kg": round(avg_weight, 1) if avg_weight else None,
            "weight_change_kg": round(weight_change, 1),
            "current_bmi": latest_record.bmi(),
            "weight_category": latest_record.weight_category(),
            "start_date": start_date.date().isoformat(),
            "end_date": datetime.now().date().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating weight stats: {str(e)}")


@router.get("/withings/heart-rate/latest")
async def get_latest_heart_rate_compat(
    db: Session = Depends(get_db),
    user_id: str = Query("default_user", description="User ID")
):
    """Backward compatibility endpoint - redirects to unified heart rate endpoint."""
    try:
        record = db.query(WithingsHeartRate)\
                   .filter(WithingsHeartRate.user_id == user_id)\
                   .order_by(WithingsHeartRate.datetime.desc())\
                   .first()
        
        if not record:
            raise HTTPException(status_code=404, detail="No heart rate data found")
        
        return {
            "id": record.id,
            "user_id": record.user_id,
            "datetime": record.datetime.isoformat() if record.datetime else None,
            "heart_rate_bpm": record.heart_rate_bpm,
            "systolic_bp_mmhg": record.systolic_bp_mmhg,
            "diastolic_bp_mmhg": record.diastolic_bp_mmhg,
            "bp_category": record.bp_category()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving latest heart rate: {str(e)}")
