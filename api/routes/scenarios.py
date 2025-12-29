"""
API routes for scenarios and hypothesis evaluation.
"""

from fastapi import APIRouter, Query, Depends
from typing import Optional
from api.auth import verify_api_key
from pam_world import WorldPAM, load_config
from database import Database
import os

router = APIRouter()

# Global PAM instance (initialized on startup)
_pam: Optional[WorldPAM] = None
_db: Optional[Database] = None


def get_pam() -> WorldPAM:
    """Get PAM instance."""
    global _pam
    if _pam is None:
        config_path = os.getenv("PAM_CONFIG", "world_config.json")
        db_path = os.getenv("PAM_DB_PATH", "pam_data.db")
        cfg = load_config(config_path, validate=True)
        _pam = WorldPAM(cfg, db_path=db_path)
    return _pam


def get_db() -> Database:
    """Get database instance."""
    global _db
    if _db is None:
        db_path = os.getenv("PAM_DB_PATH", "pam_data.db")
        _db = Database(db_path)
    return _db


@router.get("/scenarios")
async def list_scenarios(api_key: str = Depends(verify_api_key)):
    """List all available scenarios/hypotheses."""
    pam = get_pam()
    scenarios = [
        {
            "name": h.name,
            "prior": h.prior,
            "signals": h.signals
        }
        for h in pam.cfg.hypotheses
    ]
    return {"scenarios": scenarios}


@router.get("/evaluate/{scenario}")
async def evaluate_scenario(
    scenario: str,
    country: Optional[str] = Query(None),
    simulate: int = Query(0, ge=0, le=10000),
    api_key: str = Depends(verify_api_key)
):
    """Evaluate a scenario."""
    pam = get_pam()
    
    if scenario not in pam.hyps:
        return {"error": f"Unknown scenario: {scenario}"}, 404
    
    p, mean, ci, details = pam.evaluate(scenario, country=country, simulate=simulate)
    
    result = {
        "scenario": scenario,
        "probability": p,
        "country": country,
        "signals": [
            {
                "name": name,
                "value": val,
                "weight": w
            }
            for name, val, w in details
        ]
    }
    
    if mean is not None and ci is not None:
        result["monte_carlo"] = {
            "mean": mean,
            "confidence_interval": {
                "low": ci[0],
                "high": ci[1]
            }
        }
    
    return result


@router.get("/history/{scenario}")
async def get_history(
    scenario: str,
    days: int = Query(30, ge=1, le=365),
    country: Optional[str] = Query(None),
    api_key: str = Depends(verify_api_key)
):
    """Get historical evaluations for a scenario."""
    db = get_db()
    history = db.get_hypothesis_history(scenario, days=days, country=country)
    return {
        "scenario": scenario,
        "country": country,
        "days": days,
        "history": history
    }

