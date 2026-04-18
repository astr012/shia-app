from fastapi import APIRouter
from app.dependencies import classifier

router = APIRouter(prefix="/api/ml", tags=["ML"])

@router.get("/status")
async def get_ml_status():
    """Get metadata about the loaded ML gesture classifier model."""
    return {
        "status": "online",
        "model": classifier.get_status()
    }
