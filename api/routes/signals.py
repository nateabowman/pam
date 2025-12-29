"""
API routes for signals.
"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
from api.auth import verify_api_key
from database import Database
import os

router = APIRouter()


def get_db() -> Database:
    """Get database instance."""
    from api.routes.scenarios import get_db as _get_db
    return _get_db()


@router.get("/signals")
async def get_signals(api_key: str = Depends(verify_api_key)):
    """Get current signal values."""
    from api.routes.scenarios import get_pam
    pam = get_pam()
    
    signals = []
    for signal_name in pam.signals:
        # Compute current signal value
        try:
            value = pam.compute_signal(signal_name)
            signals.append({
                "name": signal_name,
                "value": value,
                "weight": pam.signals[signal_name].weight,
                "description": pam.signals[signal_name].description
            })
        except Exception:
            signals.append({
                "name": signal_name,
                "value": 0.0,
                "error": "Failed to compute"
            })
    
    return {"signals": signals}


@router.get("/signals/{signal_name}/history")
async def get_signal_history(
    signal_name: str,
    days: int = Query(30, ge=1, le=365),
    country: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key)
):
    """Get historical signal values."""
    db = get_db()
    history = db.get_signal_history(signal_name, days=days, country=country)
    return {
        "signal": signal_name,
        "country": country,
        "days": days,
        "history": history
    }

